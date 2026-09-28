"""IMF World Economic Outlook via the IMF DataMapper API.

Why this source exists: the design document records that general government
debt (`GC.DOD.TOTL.GD.ZS`) was dropped from the risk criteria because the
World Bank reports it for 3 of the 7 countries tested, and the missing ones
were Finland, Lithuania and Portugal - euro-area states, which report on a
Maastricht basis that the WDI series does not carry. That removed debt from
the model for a reason that was about the *publisher*, not about the
indicator. WEO carries it for 226 countries (verified 2026-09-28), including
every one that was missing.

The DataMapper is a plain JSON endpoint with no key and no registration, and
it answers with the full country x year matrix in one call, so this is
dramatically cheaper than the World Bank path (1 request, not 40).

PROJECTION HAZARD, AND WHY THE YEAR IS PINNED
- WEO rows mix reported actuals with projections. The `GGXWDG_NGDP` response
  runs to 2031 even though today is 2026: the years past the actuals boundary
  are IMF forecasts, and taking "the latest year" would silently ingest a
  five-year-ahead projection and label it as observed debt.
- The year is therefore pinned to `_ACTUAL_YEAR` rather than discovered. A
  relative-ranking tool should not restyle 211 countries because a new WEO
  release revised a historical figure or added a projection year. Refresh it
  deliberately, with a comment, once the intended edition's actuals are in.
"""
from __future__ import annotations

import httpx

from ..db import now
from ..models import Observation

DATAMAPPER = "https://www.imf.org/external/datamapper/api/v1"

# WEO actuals lag the current year (the October edition reports through the
# prior year). Pinned one year back from "now" so we always land on reported
# figures. Bump deliberately, never derive from today's date.
_ACTUAL_YEAR = 2024

# metric_id -> WEO series code. Only series that add information the World
# Bank does not already carry are here; duplicating GDP or current account
# from a second publisher would add a reconciliation problem and no data.
SERIES: dict[str, str] = {
    "govt_debt_pct_gdp": "GGXWDG_NGDP",
}

# Coverage floor. Measured 2026-09-28: GGXWDG_NGDP returned 226 countries
# (vs 211 in the World Bank risk universe), so the floor sits below the
# universe size on purpose - the IMF tracks economies the Bank does not.
_MIN_COVERAGE = 150


def fetch(iso3_list: list[str]) -> list[Observation]:
    fetched_at = now()
    observations: list[Observation] = []
    for metric_id, code in SERIES.items():
        resp = httpx.get(f"{DATAMAPPER}/{code}", timeout=90.0, follow_redirects=True)
        resp.raise_for_status()
        years_by_country: dict[str, dict[str, float]] = resp.json()["values"].get(code, {})
        kept = 0
        for iso3, years in years_by_country.items():
            raw = years.get(str(_ACTUAL_YEAR))
            if raw is None:
                continue
            observations.append(Observation(
                iso3=iso3, metric_id=metric_id, period=str(_ACTUAL_YEAR),
                value=float(raw), fetched_at=fetched_at,
            ))
            kept += 1
        if kept < _MIN_COVERAGE:
            raise RuntimeError(
                f"IMF WEO {code} returned {kept} countries for {_ACTUAL_YEAR}, "
                f"expected {_MIN_COVERAGE}+. Refusing to store a thin WEO pull."
            )
    return observations
