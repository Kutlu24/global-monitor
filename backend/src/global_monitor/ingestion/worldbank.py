"""World Bank Open Data API - no key required, continuous updates. Covers
the economic and most of the social dimension (GDP, population, trade %
GDP, health/education indicators) plus one of the two sanctioned military
series (military expenditure % GDP, alongside SIPRI's own numbers).

Every indicator code below was verified live against the real API
(2026-09-27) before being added here.
"""
from __future__ import annotations

import httpx

from ..db import now
from ..models import Observation

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
