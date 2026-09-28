"""World Bank Open Data API - no key required, continuous updates. Covers
the economic and most of the social dimension (GDP, population, trade %
GDP, health/education indicators) plus one of the two sanctioned military
series (military expenditure % GDP, alongside SIPRI's own numbers).

Every indicator code below was verified live against the real API
(2026-09-27) before being added here.
"""
from __future__ import annotations

import time

import httpx

from .. import db
from ..db import now
from ..models import Country, Observation

BASE_URL = "https://api.worldbank.org/v2"

# metric_id -> World Bank indicator code. Population and GDP double as the
# weight_metric_id for weighted_mean ratio metrics elsewhere (see metrics.py).
INDICATORS: dict[str, str] = {
    "gdp_current_usd": "NY.GDP.MKTP.CD",
    "population_total": "SP.POP.TOTL",
    "military_exp_pct_gdp": "MS.MIL.XPND.GD.ZS",
    "trade_pct_gdp": "NE.TRD.GNFS.ZS",
    "life_expectancy_years": "SP.DYN.LE00.IN",
    "secondary_enrollment_pct": "SE.SEC.ENRR",
}


_MRV_WINDOW = 6  # years of history to scan per country/indicator - see fetch()'s own comment

# Risk-simulator criteria inputs (docs/risk-model.md). Kept in a SEPARATE map
# from INDICATORS above, not merged into it: they are fetched for a much wider
# country universe (every World Bank country with coordinates, ~211) than the
# bloc/major-economy set, and they are read per-country by risk.py for
# percentile ranks rather than aggregated into bloc averages. Merging them
# would mean either dragging Comtrade/SIPRI/GDELT to 211 countries or making
# the narrow pass 20x more expensive.
RISK_INDICATORS: dict[str, str] = {
    # Also in INDICATORS above, deliberately repeated: the Infrastructure &
    # Health criterion requires ALL its indicators, and life expectancy is
    # only fetched for the ~48-country bloc universe by the narrow pass. A
    # single narrow-pass copy would cap that criterion's coverage at 48
    # countries and silently drop the other ~160 from the ranking.
    "life_expectancy_years": "SP.DYN.LE00.IN",
    "gdp_per_capita_ppp": "NY.GDP.PCAP.PP.KD",
    "gdp_growth_3y_pct": "NY.GDP.MKTP.KD.ZG",
    "industry_pct_gdp": "NV.IND.TOTL.ZS",
    "current_account_pct_gdp": "BN.CAB.XOKA.GD.ZS",
    "unemployment_pct": "SL.UEM.TOTL.ZS",
    "gini_index": "SI.POV.GINI",
    "poverty_headcount_pct": "SI.POV.DDAY",
    "female_labor_participation_pct": "SL.FAM.WORK.FE.ZS",
    "health_exp_per_capita_usd": "SH.XPD.CHEX.PC.CD",
    "physicians_per_1000": "SH.MED.PHYS.ZS",
    "internet_users_pct": "IT.NET.USER.ZS",
    "co2_per_capita_t": "EN.GHG.CO2.PC.CE.AR5",
    "renewable_electricity_pct": "EG.ELC.RNEW.ZS",
    "forest_area_pct": "AG.LND.FRST.ZS",
    "fossil_fuel_energy_pct": "EG.USE.COMM.FO.ZS",
    "fuel_exports_pct": "TX.VAL.FUEL.ZS.UN",
    "age_dependency_pct": "SP.POP.DPND",
    "fertility_rate": "SP.DYN.TFRT.IN",
    "population_growth_pct": "SP.POP.GROW",
}

# A risk indicator covering fewer countries than this means the response was
# throttled or partial, NOT that the indicator is sparse - every code above was
# verified to return 150+ countries on a healthy call (2026-09-28). The World
# Bank API throttles aggressively: IT.NET.USER.ZS returned 221 countries on one
# call and 39 on the next, and a burst of calls got most indicators down to
# 1-9 countries. Proceeding on that would silently shrink the country universe,
# so a thin response is retried and then raised.
_MIN_RISK_COVERAGE = 60

# Metrics stored as a multi-year mean instead of the latest single value.
_SMOOTHED_YEARS = {"gdp_growth_3y_pct": 3}

# The full metric set the risk simulator scores on, across all three
# publishers. Used by the freshness gate below, so it must include the two
# non-World-Bank series that pipeline.run_source("worldbank_risk") stores.
RISK_METRIC_IDS: frozenset[str] = frozenset(RISK_INDICATORS) | {
    "govt_debt_pct_gdp",  # IMF WEO
    "mean_years_schooling",  # UNDP
    "hdi",  # UNDP (pre-existing, ingested here on the wide universe)
}

# How stale the risk inputs may get before they are re-fetched.
# The three sources publish on annual or semi-annual cycles (WDI annually,
# WEO twice a year, HDR once a year alongside the Human Development Report),
# so 30 days is already far more often than the data can actually have
# changed. This exists because `ingest all` runs unconditionally on every
# container start (docker-entrypoint.sh) and the risk pass is by far the most
# expensive source in it - ~120 paginated requests across 211 countries.
# Without this, every `docker compose restart` re-pulled the entire world for
# data that was already sitting in the persistent volume.
_RISK_REFRESH_DAYS = 30


def risk_inputs_fresh(max_age_days: int = _RISK_REFRESH_DAYS) -> bool:
    """True when the risk observations already in the DB are recent enough to
    skip the ~120-request fetch. Thin wrapper over the shared helper so callers
    do not have to import the metric set themselves."""
    return db.metrics_fetched_within(RISK_METRIC_IDS, max_age_days)


def _wb_get(path: str, params: dict, tries: int = 4) -> object:
    """GET with exponential backoff. The World Bank API throttles by silently
    returning a near-empty (but well-formed, 200 OK) body, so a plain
    raise_for_status() is not enough - the retry has to be driven by the
    caller checking the payload, which is what the coverage assertion in
    fetch_risk_inputs() does."""
    delay = 2.0
    last: Exception | None = None
    for _ in range(tries):
        try:
            resp = httpx.get(f"{BASE_URL}{path}", params=params, timeout=45.0)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001 - retried, then re-raised below
            last = exc
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"World Bank GET {path} failed after {tries} attempts: {last}")


def fetch_country_universe() -> list[Country]:
    """Every real (non-aggregate) country the World Bank knows, with the
    lat/lon/income/region metadata the risk universe needs. `region.id == "NA"`
    is World Bank's marker for aggregate rows (World, Euro area, "Arab World"),
    which are not countries and must never be scored. 211 of 217 entries carry
    coordinates (verified 2026-09-28); the 6 without are dropped here because
    the isolation criterion is a distance calculation."""
    payload = _wb_get("/country", {"format": "json", "per_page": "400"})
    if not (isinstance(payload, list) and len(payload) == 2 and isinstance(payload[1], list)):
        raise RuntimeError(f"World Bank country endpoint returned an unexpected shape: {payload}")
    out: list[Country] = []
    for row in payload[1]:
        if row.get("region", {}).get("id") == "NA":
            continue
        # World Bank sends "" rather than null for the handful of territories
        # with no coordinates (6 of 217, verified 2026-09-28), so a plain
        # `is None` check lets an empty string through and dies in float().
        try:
            lat, lon = float(row.get("latitude") or ""), float(row.get("longitude") or "")
        except ValueError:
            continue
        out.append(Country(
            iso3=row["id"], name=row["name"], latitude=lat, longitude=lon,
            income_level=(row.get("incomeLevel") or {}).get("value"),
            region=(row.get("region") or {}).get("value"),
            lending_type=(row.get("lendingType") or {}).get("value"),
        ))
    if len(out) < 150:
        raise RuntimeError(
            f"Country universe came back with only {len(out)} countries; expected 150+. "
            "Treating this as a throttled response rather than writing a tiny universe."
        )
    return out


def _mean_of_recent(rows: list[dict], years: int) -> dict[str, tuple[str, float]]:
    """Per country, the arithmetic mean of its most recent N annual values.

    Used for real GDP growth. A single year is a flow, not a level: Niger was
    97th percentile on 2024 growth (8.3%) while 4th on GDP per capita, and
    Germany fell to 10th on -0.5%. Averaging N years removes the one-year
    weather but NOT the low-base effect - so the caller also down-weights the
    smoothed growth against the GDP-per-capita level it is mixed with."""
    buckets: dict[str, list[tuple[str, float]]] = {}
    for row in rows:
        iso3, period, value = row.get("countryiso3code"), row.get("date"), row.get("value")
        if not iso3 or period is None or value is None:
            continue
        buckets.setdefault(iso3, []).append((str(period), float(value)))
    out: dict[str, tuple[str, float]] = {}
    for iso3, series in buckets.items():
        chosen = sorted(series, key=lambda p: p[0], reverse=True)[:years]
        if chosen:
            out[iso3] = (chosen[0][0], sum(v for _, v in chosen) / len(chosen))
    return out


def _latest_non_null(rows: list[dict]) -> dict[str, tuple[str, float]]:
    """Per country, the single most recent row that actually HAS a value."""
    latest: dict[str, tuple[str, float]] = {}
    for row in rows:
        iso3, period, value = row.get("countryiso3code"), row.get("date"), row.get("value")
        if not iso3 or period is None or value is None:
            continue
        if iso3 not in latest or str(period) > latest[iso3][0]:
            latest[iso3] = (str(period), float(value))
    return latest


def fetch_risk_inputs(iso3_list: list[str] | None = None) -> list[Observation]:
    """Fetches RISK_INDICATORS for the WIDE universe and refuses to return a
    suspiciously thin one.

    Requests an explicit `date` window rather than `mrv`: verified live
    2026-09-28, `date=2015:2024` returned 221 countries for IT.NET.USER.ZS
    where `MRV=1` on the same call returned 39, and `mrv=1` on a second
    indicator returned 1. Either would silently shrink the universe instead of
    failing - the exact failure that scored 0 countries without raising during
    prototyping."""
    fetched_at = now()
    if not iso3_list:
        iso3_list = [c.iso3 for c in fetch_country_universe()]
    observations: list[Observation] = []
    thin: list[str] = []
    for metric_id, indicator_code in RISK_INDICATORS.items():
        smoother = _SMOOTHED_YEARS.get(metric_id)
        # A chunked size that keeps the semicolon-joined URL well under the
        # ~2000-char limit servers enforce - 211 codes in one URL gets rejected.
        for start in range(0, len(iso3_list), 40):
            chunk = iso3_list[start:start + 40]
            payload = _wb_get(
                f"/country/{';'.join(chunk)}/indicator/{indicator_code}",
                {"format": "json", "per_page": "20000", "date": "2015:2024"},
            )
            if isinstance(payload, list) and len(payload) == 2 and isinstance(payload[1], list):
                series = (_mean_of_recent(payload[1], smoother) if smoother
                          else _latest_non_null(payload[1]))
                for iso3, (period, value) in series.items():
                    observations.append(Observation(
                        iso3=iso3, metric_id=metric_id, period=period,
                        value=value, fetched_at=fetched_at,
                    ))
            time.sleep(0.5)
        covered = {o.iso3 for o in observations if o.metric_id == metric_id}
        if len(covered) < _MIN_RISK_COVERAGE:
            thin.append(f"{metric_id}({indicator_code}): {len(covered)} countries")
    if thin:
        raise RuntimeError(
            "Risk indicator coverage collapsed - refusing to store a partial universe. "
            "Thin or empty: " + "; ".join(thin)
        )
    return observations


def _fetch_indicator(iso3_list: list[str], indicator_code: str) -> list[dict]:
    """One call per indicator, all requested countries at once (World Bank
    accepts a semicolon-joined country list). Requests a window of recent
    years (`mrv=_MRV_WINDOW`), not just the single most recent one - see
    fetch()'s own comment for why `mrv=1` alone isn't safe."""
    countries = ";".join(iso3_list)
    url = f"{BASE_URL}/country/{countries}/indicator/{indicator_code}"
    params = {"format": "json", "mrv": str(_MRV_WINDOW), "per_page": "1000"}
    resp = httpx.get(url, params=params, timeout=30.0)
    resp.raise_for_status()
    payload = resp.json()
    # World Bank's own error shape: [{"message": [...]}] instead of the
    # normal [metadata, data] pair - surface it rather than crashing on
    # `payload[1]` with a confusing IndexError.
    if isinstance(payload, list) and len(payload) == 2 and isinstance(payload[1], list):
        return payload[1] or []
    raise RuntimeError(f"World Bank API returned an unexpected shape for {indicator_code}: {payload}")


def fetch(iso3_list: list[str]) -> list[Observation]:
    """CONFIRMED LIVE (2026-09-27): `mrv=1` does NOT reliably return each
    country's most recent NON-NULL observation, despite what World Bank's
    own docs suggest - many indicators pre-create a database row for the
    current year before any value has actually been reported, and mrv=1
    happily returns that row with value=None. This silently produced an
    all-null result for secondary_enrollment_pct (every one of the 48
    tracked countries) and an all-null trade_pct_gdp for the US
    specifically, both then correctly excluded downstream (aggregate.py
    already filters `value is not None`) but with NO real data to fall
    back to - a systematic "N/A" for those metrics.

    Fixed by requesting a window of recent years per country
    (`mrv=_MRV_WINDOW`) and keeping, per country, only the single most
    recent entry that actually HAS a value - never storing a null
    placeholder when a real (if slightly older) observation exists within
    the window."""
    fetched_at = now()
    observations: list[Observation] = []
    for metric_id, indicator_code in INDICATORS.items():
        latest_real_by_iso3: dict[str, dict] = {}
        for row in _fetch_indicator(iso3_list, indicator_code):
            iso3 = row.get("countryiso3code")
            period = row.get("date")
            if not iso3 or period is None or row.get("value") is None:
                continue
            existing = latest_real_by_iso3.get(iso3)
            if existing is None or str(period) > str(existing["date"]):
                latest_real_by_iso3[iso3] = row
        for row in latest_real_by_iso3.values():
            observations.append(Observation(
                iso3=row["countryiso3code"], metric_id=metric_id, period=str(row["date"]),
                value=row["value"], fetched_at=fetched_at,
            ))
    return observations
