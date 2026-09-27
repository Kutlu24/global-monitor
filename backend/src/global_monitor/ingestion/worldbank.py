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


def _fetch_indicator(iso3_list: list[str], indicator_code: str) -> list[dict]:
    """One call per indicator, all requested countries at once (World Bank
    accepts a semicolon-joined country list) - `mrv=1` returns each
    country's single most-recent non-null observation, so we don't need to
    know which year is "current" ahead of time."""
    countries = ";".join(iso3_list)
    url = f"{BASE_URL}/country/{countries}/indicator/{indicator_code}"
    params = {"format": "json", "mrv": "1", "per_page": "1000"}
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
    fetched_at = now()
    observations: list[Observation] = []
    for metric_id, indicator_code in INDICATORS.items():
        for row in _fetch_indicator(iso3_list, indicator_code):
            iso3 = row.get("countryiso3code")
            value = row.get("value")
            period = row.get("date")
            if not iso3 or period is None:
                continue
            observations.append(Observation(iso3=iso3, metric_id=metric_id, period=str(period),
                                              value=value, fetched_at=fetched_at))
    return observations
