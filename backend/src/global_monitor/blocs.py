"""THE single canonical bloc -> country membership mapping. Every ETL
module and aggregate.py compute their country lists from `db.get_current_members`
(which reads the `bloc_membership` rows this module seeds) - adding or
removing a member is a change here only, never scattered through ingestion
code.

BRICS is modeled as two bloc rows sharing the same generic mechanism:
`brics` (current/BRICS+, the real membership as of this expansion) and
`brics5` (the original five, frozen) - see the plan's "Resolved decisions"
for why. Only `brics` appears in the main /compare/{pair} structure;
`brics5` is a secondary historical view linked from /bloc/brics.

Saudi Arabia was invited to join BRICS+ in the 2023 Johannesburg summit
announcement but its accession status has stayed publicly ambiguous since
- deliberately excluded here rather than guessed. Revisit if it resolves.
"""
from __future__ import annotations

from . import db
from .models import Bloc, BlocMembership, Country

# --- Blocs ---

BLOCS = [
    Bloc("brics", "BRICS+", "brics", "Brazil, Russia, India, China, South Africa, and the 2024-25 expansion members"),
    Bloc("brics5", "BRICS (original five)", "brics5", "The founding five BRICS members, before the 2024-25 expansion"),
    Bloc("eu", "European Union", "eu", "The 27 current EU member states (post-Brexit)"),
    Bloc("us", "United States", "us", "The United States, tracked as a single-country bloc for comparison"),
    Bloc("usmca", "USMCA (NAFTA)", "usmca", "United States, Canada, and Mexico under USMCA (formerly NAFTA)"),
]

# --- Countries referenced below (iso3, name) ---

_BRICS_CORE_5 = [
    ("BRA", "Brazil"), ("RUS", "Russia"), ("IND", "India"), ("CHN", "China"), ("ZAF", "South Africa"),
]
_BRICS_EXPANSION = [
    ("EGY", "Egypt"), ("ETH", "Ethiopia"), ("IRN", "Iran"), ("ARE", "United Arab Emirates"), ("IDN", "Indonesia"),
]
_EU_27 = [
    ("AUT", "Austria"), ("BEL", "Belgium"), ("BGR", "Bulgaria"), ("HRV", "Croatia"), ("CYP", "Cyprus"),
    ("CZE", "Czechia"), ("DNK", "Denmark"), ("EST", "Estonia"), ("FIN", "Finland"), ("FRA", "France"),
    ("DEU", "Germany"), ("GRC", "Greece"), ("HUN", "Hungary"), ("IRL", "Ireland"), ("ITA", "Italy"),
    ("LVA", "Latvia"), ("LTU", "Lithuania"), ("LUX", "Luxembourg"), ("MLT", "Malta"), ("NLD", "Netherlands"),
    ("POL", "Poland"), ("PRT", "Portugal"), ("ROU", "Romania"), ("SVK", "Slovakia"), ("SVN", "Slovenia"),
    ("ESP", "Spain"), ("SWE", "Sweden"),
]
_US = [("USA", "United States")]
_USMCA_PARTNERS = [("CAN", "Canada"), ("MEX", "Mexico")]

ALL_COUNTRIES = dict(_BRICS_CORE_5 + _BRICS_EXPANSION + _EU_27 + _US + _USMCA_PARTNERS)

# --- Membership: (bloc_id, iso3, effective_from, effective_to) ---
# Dates are real accession dates, not placeholders - needed so historical
# aggregation (aggregate.py) can use period-correct membership later.

_BRICS_CORE_MEMBERSHIP = [
    ("brics", "BRA", "2009-06-16", None), ("brics", "RUS", "2009-06-16", None),
    ("brics", "IND", "2009-06-16", None), ("brics", "CHN", "2009-06-16", None),
    ("brics", "ZAF", "2011-04-14", None),
]
_BRICS_EXPANSION_MEMBERSHIP = [
    ("brics", "EGY", "2024-01-01", None), ("brics", "ETH", "2024-01-01", None),
    ("brics", "IRN", "2024-01-01", None), ("brics", "ARE", "2024-01-01", None),
    ("brics", "IDN", "2025-01-01", None),
]
_BRICS5_MEMBERSHIP = [(bloc_id.replace("brics", "brics5"), iso3, eff_from, eff_to)
                       for bloc_id, iso3, eff_from, eff_to in _BRICS_CORE_MEMBERSHIP]
_EU_MEMBERSHIP = [("eu", iso3, "1993-11-01", None) for iso3, _ in _EU_27]
_US_MEMBERSHIP = [("us", "USA", "1789-03-04", None)]
_USMCA_MEMBERSHIP = [("usmca", "USA", "1994-01-01", None), ("usmca", "CAN", "1994-01-01", None),
                      ("usmca", "MEX", "1994-01-01", None)]

MEMBERSHIP = (
    _BRICS_CORE_MEMBERSHIP + _BRICS_EXPANSION_MEMBERSHIP + _BRICS5_MEMBERSHIP
    + _EU_MEMBERSHIP + _US_MEMBERSHIP + _USMCA_MEMBERSHIP
)


def seed() -> None:
    """Idempotent - safe to call on every boot (see docker-entrypoint.sh)."""
    for bloc in BLOCS:
        db.upsert_bloc(bloc)
    for iso3, name in ALL_COUNTRIES.items():
        db.upsert_country(Country(iso3, name))
    for bloc_id, iso3, effective_from, effective_to in MEMBERSHIP:
        db.upsert_membership(BlocMembership(bloc_id, iso3, effective_from, effective_to))


def all_tracked_iso3() -> list[str]:
    """Every country any bloc currently cares about - what ingestion
    modules fetch for, computed fresh (not hardcoded) so adding a member
    above is the only change needed to also start pulling their data."""
    return sorted(ALL_COUNTRIES.keys())
