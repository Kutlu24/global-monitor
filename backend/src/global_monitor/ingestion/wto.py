"""WTO Timeseries API: commercial services exports and imports (`ITS_CS_AX6` / `ITS_CS_AM6`,
sector `SOX` = commercial services, partner `000` = world, million US$).

Comtrade covers goods only, so this is the services side of trade. Reporters are numeric WTO
codes; `/reporters` maps them to ISO3. The API needs a free subscription key (Standard product on
apiportal.wto.org) sent as `Ocp-Apim-Subscription-Key`; without one this raises rather than
storing nothing silently. A country with no row did not report that year.
"""
from __future__ import annotations

import httpx

from ..config import settings
from ..db import now
from ..models import Observation

BASE = "https://api.wto.org/timeseries/v1"
INDICATORS = {"services_exports_usd": "ITS_CS_AX6", "services_imports_usd": "ITS_CS_AM6"}
_YEARS_BACK = 3
_MIN_COVERAGE = 20  # of the ~48 tracked countries


def _get(path: str, params: dict, key: str) -> list | dict:
    resp = httpx.get(f"{BASE}/{path}", params=params, headers={"Ocp-Apim-Subscription-Key": key},
                     timeout=120.0, follow_redirects=True)
    resp.raise_for_status()
    return resp.json()


def _latest(rows: list[dict], code_to_iso3: dict[str, str]) -> dict[str, tuple[int, float]]:
    """Newest year per country, value converted from million US$ to US$."""
    best: dict[str, tuple[int, float]] = {}
    for r in rows:
        iso3 = code_to_iso3.get(str(r.get("ReportingEconomyCode")))
        value = r.get("Value")
        if iso3 is None or value is None:
            continue
        year = int(r["Year"])
        if iso3 not in best or year > best[iso3][0]:
            best[iso3] = (year, float(value) * 1e6)
    return best


def fetch(iso3_list: list[str], last_year: int) -> list[Observation]:
    key = settings.wto_api_key
    if not key:
        raise RuntimeError("WTO: no API key (set GLOBAL_MONITOR_WTO_API_KEY; free Standard subscription at apiportal.wto.org)")
    wanted = set(iso3_list)
    code_to_iso3 = {r["code"]: r["iso3A"] for r in _get("reporters", {"lang": 1}, key)
                    if r.get("iso3A") in wanted}
    out: list[Observation] = []
    fetched_at = now()
    for metric_id, indicator in INDICATORS.items():
        data = _get("data", {"i": indicator, "r": ",".join(code_to_iso3), "p": "000", "pc": "SOX",
                             "ps": f"{last_year - _YEARS_BACK}-{last_year}", "fmt": "json", "mode": "codes",
                             "max": 100000}, key)
        best = _latest(data.get("Dataset", []), code_to_iso3)
        if len(best) < _MIN_COVERAGE:
            raise RuntimeError(f"WTO {indicator}: only {len(best)} countries, expected {_MIN_COVERAGE}+. "
                               "Refusing to store a thin pull.")
        for iso3, (year, value) in best.items():
            out.append(Observation(iso3=iso3, metric_id=metric_id, period=str(year), value=value,
                                   fetched_at=fetched_at))
    return out
