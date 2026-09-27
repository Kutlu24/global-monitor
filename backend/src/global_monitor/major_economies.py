"""The "major economies" country-comparison module - a SEPARATE concept
from bloc_membership. These 20 countries are compared individually
(country vs. country), not aggregated into a bloc, so this module never
touches bloc_membership/bloc_aggregates - it only needs `countries` rows
and per-country `observations` (already stored regardless of bloc
membership).

Selection criterion: IMF's "Advanced Economy" classification, top 20 by
nominal GDP, restricted to sovereign states with a standard World Bank
country entry. This deliberately excludes China and India (the world's
2nd and 5th-largest economies by GDP) - IMF classifies both as "Emerging
Market and Developing Economies," not advanced, and both are already
tracked at bloc level via BRICS anyway. Also excludes Hong Kong SAR/Macao
SAR/Taiwan - real advanced economies in IMF's own list, but none have a
standard sovereign-state World Bank entry, which would need special-cased
ingestion for three small economies at real added complexity.

11 of these 20 are already tracked via bloc_membership (US, and 9 EU
members, and Canada via USMCA) - only the other 9 are new here.
"""
from __future__ import annotations

from . import db
from .blocs import ALL_COUNTRIES
from .models import Country

# New countries not already covered by blocs.ALL_COUNTRIES.
_NEW_COUNTRIES = {
    "JPN": "Japan", "GBR": "United Kingdom", "KOR": "South Korea", "AUS": "Australia",
    "CHE": "Switzerland", "SGP": "Singapore", "ISR": "Israel", "NOR": "Norway",
}

# The full top-20 list, roughly GDP-ranked (exact live ranking is computed
# from real ingested data at display time - this ordering is just the
# editorial "which 20 countries" choice, same as BRICS membership is).
MAJOR_ECONOMY_ISO3 = [
    "USA", "JPN", "DEU", "GBR", "FRA", "ITA", "CAN", "KOR", "AUS", "ESP",
    "NLD", "CHE", "SGP", "IRL", "ISR", "AUT", "NOR", "BEL", "SWE", "DNK",
]


def seed() -> None:
    for iso3, name in _NEW_COUNTRIES.items():
        db.upsert_country(Country(iso3, name))


def all_iso3() -> list[str]:
    return sorted(MAJOR_ECONOMY_ISO3)


def country_name(iso3: str) -> str:
    return _NEW_COUNTRIES.get(iso3) or ALL_COUNTRIES.get(iso3, iso3)
