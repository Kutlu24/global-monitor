"""Risk simulator - data-driven scoring. Replaces the 19 hand-scored
countries x 11 hand-assigned criteria that used to live in
`frontend/src/lib/risk.ts` (a port of the standalone `risk-simulator-pro`
Streamlit app, scored 0-10 by hand with no ETL behind it). Full rationale,
the excluded criteria and the engineering constraints are in
docs/risk-model.md; the short version:

WHAT CHANGED AND WHY
- Six STRUCTURAL criteria, every one computed from World Bank Open Data. The
  four that had no source in World Bank/IMF/OECD/UNDP - Nuclear Risk, Political
  Neutrality, Public Preparedness, Cybersecurity - were REMOVED rather than
  kept as judgment calls, so nothing on the page is a hand-assigned number
  wearing a data label.
- Proximity to conflict is now a SEPARATE exposure axis in kilometres, computed
  PER SCENARIO from real flashpoint coordinates, instead of a weighted term
  inside a single score. This is what the old model structurally could not
  express: with capital-to-capital distance, Poland, the Baltics, Turkey and
  Ukraine all came out at an identical 0 km from a Russia-NATO epicentre set,
  and then Belarus ranked 3rd as "Resilient" while 31 km from the front.
- The two axes are never averaged into each other and never reduced to a
  quadrant. The score is named `structural_score`, not `resilience_score`,
  because "resilience" is a verdict and "structural" is what is measured.
- The universe is every World Bank country with coordinates (~211), not a
  19-country allowlist, which is what made most of Europe render as "no data".

SCORING
- Each indicator becomes a percentile rank across the universe (ties
  averaged); a criterion is the WEIGHTED mean of the indicators a country
  actually has. Percentile rather than min-max because this is explicitly a
  RELATIVE standing tool and because min-max is hostage to outliers and would
  restyle every country whenever one is added.
- Weight matters because a level and a flow are not comparable units. GDP per
  capita (a stock) carries weight 3; the 3-year mean growth rate carries weight
  1. At 1:1, Niger scored mid-table on 4th-percentile income because poor
  countries grow fast off a low base, and Germany fell to 10th on one recession
  year. Now Niger 43.6 -> 29.9, Mali 51.4 -> 35.4, Germany 61.2.
- A country needs at least half of a criterion's total WEIGHT to be scored on
  it. The earlier "every indicator of every criterion" rule ranked 112 of 211
  countries and excluded almost every fragile state the user asked about;
  because `energy_imports_pct` is a trade-flow identity, a net fuel exporter
  had no value for it, so it was missing for exactly the countries under energy
  stress. Now 178 of 211, and `completeness` plus the named missing indicators
  are returned per country rather than dropped silently.
- Two-sided indicators (current account, fertility, population growth) score
  by distance from the cross-country median, not by direction - a huge
  current-account deficit and a huge surplus are both fragile.

NUCLEAR POSTURE AND PARTY TO THE CONFLICT ARE FLAGS, NOT SCORES
- `NUCLEAR_ARMED` (see below) and the per-scenario `belligerents` are the only
  hand-maintained lists in the model, and the UI labels them as such. Both are
  deliberately NOT folded into the score: the six structural criteria are
  reproducible from a public API, and blending in a hand-kept binary would make
  the headline number non-reproducible - the exact "looks rigorous, isn't"
  failure this rewrite was commissioned to remove. Reported alongside the score
  instead, so "high exposure, mid structural" (Poland) and "low exposure, high
  structural" (Norway) stay visible as two separate facts.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import db

# metric_id -> direction. +1 higher is more resilient, -1 lower, 0 two-sided.
# The "life_expectancy_years" reuse is deliberate: it already exists in the
# catalogue for the social dimension, so re-fetching it would duplicate a
# metric the aggregate layer already treats as canonical.
CRITERIA: dict[str, dict] = {
    # Each indicator is (metric_id, direction, weight). Direction +1 = higher is
    # better, -1 = lower is better, 0 = closest to the cross-country median is
    # better. Weight lets a level outweigh a flow: GDP per capita is a stock,
    # growth is a rate, and averaging them 1:1 made Niger 4th-percentile on
    # income but 97th on "resilience" while Germany fell to 10th on a
    # recession. GDP per capita now carries 3x the weight of the 3-year mean
    # growth, so the level dominates and the flow only breaks ties.
    "economic_resilience": {
        "name": "Economic Resilience",
        "indicators": [
            ("gdp_per_capita_ppp", +1, 3),
            ("gdp_growth_3y_pct", +1, 1),
            ("govt_debt_pct_gdp", -1, 1),
            ("industry_pct_gdp", +1, 1),
            ("current_account_pct_gdp", 0, 1),
        ],
    },
    "domestic_social_stability": {
        "name": "Domestic Social Stability",
        "indicators": [
            ("unemployment_pct", -1, 1),
            ("gini_index", -1, 1),
            ("poverty_headcount_pct", -1, 1),
            ("female_labor_participation_pct", +1, 1),
        ],
    },
    "infrastructure_health": {
        "name": "Human & Physical Infrastructure",
        "indicators": [
            ("life_expectancy_years", +1, 1),
            ("mean_years_schooling", +1, 1),
            ("health_exp_per_capita_usd", +1, 1),
            ("physicians_per_1000", +1, 1),
            ("internet_users_pct", +1, 1),
        ],
    },
    "climate_resilience": {
        "name": "Climate Resilience",
        "indicators": [
            ("co2_per_capita_t", -1, 1),
            ("renewable_electricity_pct", +1, 1),
            ("forest_area_pct", +1, 1),
        ],
    },
    "energy_independence": {
        "name": "Energy Independence",
        "indicators": [
            ("fossil_fuel_energy_pct", -1, 1),
            ("fuel_exports_pct", +1, 1),
        ],
    },
    "demographic_resilience": {
        "name": "Demographic Resilience",
        "indicators": [
            ("age_dependency_pct", -1, 1),
            ("fertility_rate", 0, 1),
            ("population_growth_pct", 0, 1),
        ],
    },
}

# The name the old model used for the isolation criterion. Kept only so the
# change is greppable in the git history and in docs/risk-model.md - it is NOT
# a key in CRITERIA and NOT a term in any Scenario.weights. Proximity to the
# fighting is computed in `score()` and returned as `exposure_km` /
# `exposure_percentile` beside the structural score, never summed with it.
# With isolation folded into one weighted score, Ukraine came out 17th and
# labelled "Resilient" in the Russia-NATO scenario, because its pre-war
# economic indicators were still good enough to outweigh a 186 km epicentre
# distance. "How far is this country from the fighting" and "how well does
# this country hold together" are different questions, and averaging them
# produces a number that answers neither.
LEGACY_EXPOSURE_CRITERION = "geographic_isolation"

# A criterion is scored from the indicators a country actually has, provided it
# has at least half of them. The earlier "all or nothing" rule looked rigorous
# and was actively harmful: `energy_imports_pct`, `gini_index` and
# `poverty_headcount_pct` are reported for middle- and high-income countries
# and largely absent for the poorest ones, so requiring all of them excluded
# exactly the fragile states this rewrite was commissioned to surface - Mali,
# Afghanistan, Burkina Faso and Yemen were all dropped, and of the five Sahel/
# fragile states tested only Niger survived. What each country's score is built
# from is reported back in `completeness` and surfaced in the UI, so a 3-of-4
# score is never presented as if it were 4-of-4.
_MIN_INDICATOR_FRACTION = 0.5

# Nuclear-armed states, as of 2026 (NPT recognises five NWS; the other four are
# de facto). Sources: NPT / IAEA / FAS. The only hand-maintained list in the
# model - see the module docstring for why it is not part of the composite.
# Cross-checked against SIPRI military expenditure (military_exp_pct_gdp),
# which is already tracked: every one of these should sit in the upper tail
# of global militarisation. That check is a sanity guard on this list going
# stale, not the source of truth.
NUCLEAR_ARMED: frozenset[str] = frozenset({
    "RUS",  # Russia - NWS
    "USA",  # United States - NWS
    "CHN",  # China - NWS
    "GBR",  # United Kingdom - NWS
    "FRA",  # France - NWS
    "IND",  # India
    "PAK",  # Pakistan
    "PRK",  # North Korea
    "ISR",  # Israel
})


# FRAGILITY IS A PROXY, AND THE LABEL SAYS SO
# The user asked for fragile countries to be visible in the model. The
# authoritative classification is the OECD DAC annual fragile-contexts list,
# and it is not reachable: oecd.org returns HTTP 403 to non-browser clients and
# the SDMX endpoint does not expose the list (both verified 2026-09-28), so
# ingesting it would mean a hand-typed list with a year attached and no way to
# check it had not been superseded.
#
# CPIA - the World Bank's own fragility score - is IDA-only and genuinely not
# in the public API either.
#
# What is available is the World Bank's own lending type, already returned by
# the country endpoint this module already fetches. IDA (International
# Development Association) credit means the Bank has judged a country too poor
# or too credit-impaired for ordinary IBRD terms. That is a poverty-and-
# creditworthiness signal, NOT a fragility signal: it does not capture
# conflict, institutional collapse or displacement, and it misses countries
# that are fragile but not IDA-eligible.
#
# So this is derived, named for what it is, and reported as a flag rather than
# a score. The UI must render it as "IDA credit (fragility proxy)", never
# "fragile".
def fragility_proxy(lending_type: str | None) -> bool:
    """True when the World Bank lends to this country on IDA terms.

    Deliberately excludes "Blend", which is mixed IDA/IBRD and mostly used by
    middle-income countries with real market access."""
    return (lending_type or "").strip().upper() == "IDA"


@dataclass(frozen=True)
class Scenario:
    slug: str
    name: str
    weights: dict[str, float]
    epicentres: tuple[tuple[float, float, str], ...]
    explanation: str
    not_measured: str
    # Parties to the conflict this scenario simulates, reported as a flag and
    # never mixed into a score. Same treatment as NUCLEAR_ARMED, for the same
    # reason: without it Belarus ranks 3rd and Russia 6th on "resilience"
    # (GDP pc 64th, growth 71st, industry 75th) while sitting 31 km and 595 km
    # from the front. A model of how well a country holds together has no
    # business implying that the belligerent is doing well.
    belligerents: tuple[str, ...] = ()


_EARTH_RADIUS_KM = 6371.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


# Epicentres are real flashpoint coordinates, NOT country capitals. This is the
# single most important choice in the file: capital-to-capital distance made
# every country inside the epicentre set return an identical 0 km, erasing the
# difference between Poland (border) and Spain (far), and put Sweden closer
# to the Baltics than Norway for reasons that had nothing to do with either
# country's position.
_RUSSIA_NATO = (
    (54.71, 20.51, "Kaliningrad exclave"),
    (53.90, 28.03, "Belarus-Russia border"),
    (52.10, 30.98, "Belarus-Ukraine border (Gomel)"),
    (48.50, 37.50, "Donetsk / eastern Ukraine front"),
    (54.10, 22.90, "Suwalki Gap"),
    (69.50, 28.50, "Finland-Russia border"),
)

# Generic global flashpoints, used only by the baseline scenario, which has no
# single theatre.
_GLOBAL = (
    (26.60, 56.30, "Strait of Hormuz"),
    (23.70, 120.90, "Taiwan Strait"),
    (15.50, 32.50, "Nile basin"),
    (13.00, 105.00, "Mekong basin"),
    (41.88, -87.63, "US Great Lakes"),
)

SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        slug="general-balanced-crisis",
        name="General Balanced Crisis",
        weights={
            "economic_resilience": 0.20, "domestic_social_stability": 0.20,
            "infrastructure_health": 0.20, "climate_resilience": 0.16,
            "energy_independence": 0.14, "demographic_resilience": 0.10,
        },
        epicentres=_GLOBAL,
        explanation=(
            "A baseline in which no single factor dominates: all six structural "
            "criteria carry roughly equal weight. Exposure is measured against a "
            "generic set of global flashpoints rather than one theatre, so it is "
            "rough geographic context, not a prediction for any one region."
        ),
        not_measured="No specific conflict or sector.",
        belligerents=(),
    ),
    Scenario(
        slug="russia-nato-conflict",
        name="Russia-NATO Conflict",
        weights={
            "economic_resilience": 0.20, "domestic_social_stability": 0.16,
            "infrastructure_health": 0.20, "climate_resilience": 0.12,
            "energy_independence": 0.18, "demographic_resilience": 0.14,
        },
        epicentres=_RUSSIA_NATO,
        explanation=(
            "Two separate questions, deliberately not combined into one. The "
            "structural score asks how well a country holds together on economic, "
            "social, infrastructure, climate, energy and demographic indicators. "
            "Exposure asks how far it sits from the Kaliningrad exclave, the "
            "Belarus-Russia border, Donetsk, the Suwalki Gap and the "
            "Finland-Russia border. Poland, the Baltics, Ukraine and Turkey were "
            "absent from the previous 19-country allowlist entirely."
        ),
        # Russia and Belarus are the parties to this scenario. Ukraine is a
        # target, not a party, so it is deliberately absent from the list.
        belligerents=("RUS", "BLR"),
        not_measured=(
            "Nuclear deterrence, alliance alignment, war losses and refugee "
            "flows. None are in the source data, so none are hand-scored. "
            "Nuclear-armed states and the parties to the conflict are flagged "
            "on their own axes, never folded into a score."
        ),
    ),
    Scenario(
        slug="china-us-tension",
        name="China-US Tension (Economic Crisis)",
        weights={
            "economic_resilience": 0.33, "domestic_social_stability": 0.17,
            "infrastructure_health": 0.17, "climate_resilience": 0.09,
            "energy_independence": 0.08, "demographic_resilience": 0.16,
        },
        epicentres=(
            (23.70, 120.90, "Taiwan Strait"),
            (12.00, 114.00, "South China Sea"),
            (37.57, 126.98, "Korean peninsula"),
        ),
        explanation=(
            "Economic self-sufficiency and industrial depth dominate, with "
            "isolation from the Taiwan/South China Sea theatres mattering "
            "but far less than in the Russia-NATO case."
        ),
        belligerents=("CHN", "USA"),
        not_measured="Semiconductor supply-chain position and tech decoupling specifically.",
    ),
    Scenario(
        slug="hormuz-energy-shock",
        name="Strait of Hormuz Crisis (Energy Shock)",
        weights={
            "economic_resilience": 0.20, "domestic_social_stability": 0.15,
            "infrastructure_health": 0.08, "climate_resilience": 0.09,
            "energy_independence": 0.43, "demographic_resilience": 0.05,
        },
        epicentres=((26.60, 56.30, "Strait of Hormuz"),),
        explanation=(
            "Energy independence dominates the structural score. Exposure is "
            "still reported in kilometres, but it is a separate axis rather "
            "than something folded into the total: the Gulf states sit closest "
            "to Hormuz and are also the most fuel-export-dependent, so a "
            "combined number would say the same thing twice."
        ),
        not_measured="Shipping insurance, chokepoint transit volumes, and spare oil capacity.",
    ),
    Scenario(
        slug="climate-water-wars",
        name="Climate Crisis & Water Wars",
        weights={
            "economic_resilience": 0.11, "domestic_social_stability": 0.20,
            "infrastructure_health": 0.13, "climate_resilience": 0.39,
            "energy_independence": 0.06, "demographic_resilience": 0.11,
        },
        epicentres=(
            (15.50, 32.50, "Nile basin"),
            (33.00, 44.00, "Tigris-Euphrates"),
            (13.00, 105.00, "Mekong basin"),
            (-4.00, 22.00, "Kalahari / Zambezi drought belt"),
        ),
        explanation=(
            "Climate resilience leads, followed by social stability: water "
            "access and per-capita emissions pressure matter more than income."
        ),
        not_measured="Actual freshwater availability per capita (no reliable free API for it).",
    ),
    Scenario(
        slug="tech-energy-revolution",
        name="Technological Energy Revolution",
        weights={
            "economic_resilience": 0.31, "domestic_social_stability": 0.16,
            "infrastructure_health": 0.23, "climate_resilience": 0.08,
            "energy_independence": 0.11, "demographic_resilience": 0.11,
        },
        epicentres=(
            (37.40, -122.10, "Silicon Valley"),
            (23.70, 120.90, "Taiwan semiconductor belt"),
        ),
        explanation=(
            "Diversified, innovative economies with good digital "
            "infrastructure and a young population come out ahead."
        ),
        not_measured="R&D spend and human capital directly (only proxied via internet use and demographics).",
    ),
)


def find_scenario(slug: str) -> Scenario | None:
    return next((s for s in SCENARIOS if s.slug == slug), None)


def _percentile_ranks(pairs: list[tuple[str, float]]) -> dict[str, float]:
    """(key, value) -> percentile 0-100, ties averaged."""
    ordered = sorted(pairs, key=lambda t: t[1])
    n = len(ordered)
    out: dict[str, float] = {}
    if n == 0:
        return out
    i = 0
    while i < n:
        j = i
        while j + 1 < n and ordered[j + 1][1] == ordered[i][1]:
            j += 1
        rank = ((i + j) / 2) / (n - 1) * 100 if n > 1 else 50.0
        for k in range(i, j + 1):
            out[ordered[k][0]] = rank
        i = j + 1
    return out


def _metric_values(metric_ids: set[str], iso3_list: list[str]) -> dict[str, dict[str, float]]:
    return {
        metric_id: {o.iso3: o.value for o in db.get_observations(metric_id, iso3_list)}
        for metric_id in metric_ids
    }


def _isolation_km(
    scenario: Scenario,
    countries: dict[str, tuple[float, float]],
) -> dict[str, float]:
    """Distance from each country to the NEAREST epicentre. The min() is what
    makes it an exposure measure: being far from Kaliningrad does not help if
    you are next to Donetsk."""
    out: dict[str, float] = {}
    for iso3, (lat, lon) in countries.items():
        out[iso3] = min(
            _haversine_km(lat, lon, e_lat, e_lon) for e_lat, e_lon, _ in scenario.epicentres
        ) if scenario.epicentres else 0.0
    return out


def score(scenario: Scenario) -> dict:
    """Two independent axes per country, plus a reported-only nuclear flag -
    deliberately NOT one combined "Resilient/Vulnerable" label. See
    LEGACY_EXPOSURE_CRITERION for why averaging exposure into resilience is what made
    Ukraine rank 17th and read "Resilient" in a war it is actually fighting.

    "structural_score" answers "how well does this country hold together";
    "exposure_km" answers "how far is it from the fighting". A reader gets
    both. Neither is averaged into the other, and no quadrant label is
    invented from their combination - that would reintroduce the same
    conflation under a new name.
    """
    countries = {c.iso3: (c.latitude, c.longitude)
                 for c in db.get_coordinate_countries() if c.latitude is not None and c.longitude is not None}
    if not countries:
        raise RuntimeError("No countries with coordinates - has worldbank_risk ingest run?")
    iso3_list = sorted(countries)
    names = {c.iso3: c.name for c in db.get_all_countries()}
    ida_credit = {
        c.iso3 for c in db.get_coordinate_countries() if fragility_proxy(c.lending_type)
    }

    metric_ids = {m for c in CRITERIA.values() for m, _d, _w in c["indicators"]}
    values = _metric_values(metric_ids, iso3_list)

    criterion_scores: dict[str, dict[str, float]] = {}
    missing: dict[str, set[str]] = {iso: set() for iso in iso3_list}

    for criterion_key, spec in CRITERIA.items():
        percentiles: list[tuple[str, dict[str, float]]] = []
        for metric_id, direction, _w in spec["indicators"]:
            data = values.get(metric_id, {})
            if len(data) < 30:
                raise RuntimeError(
                    f"{metric_id} has data for only {len(data)} countries. Either the "
                    "worldbank_risk ingest has not run, or it ran before this metric was "
                    "added to RISK_INDICATORS - an ingestion-state problem, not a scoring "
                    "bug. Refusing to rank on thin data."
                )
            if direction == 0:
                ordered = sorted(data.values())
                median = ordered[len(ordered) // 2]
                p = _percentile_ranks([(k, -abs(v - median)) for k, v in data.items()])
            elif direction > 0:
                p = _percentile_ranks(list(data.items()))
            else:
                p = _percentile_ranks([(k, -v) for k, v in data.items()])
            percentiles.append((metric_id, p))

        # Threshold on WEIGHT, not on indicator count: a country qualifies for a
        # criterion once it holds at least half that criterion's total weight, so
        # a missing GDP per capita (weight 3) costs it the criterion while a
        # missing current account (weight 1) does not.
        total_weight = sum(w for _, _, w in spec["indicators"])
        needed = total_weight * _MIN_INDICATOR_FRACTION
        scores: dict[str, float] = {}
        for iso in iso3_list:
            have = [(w, entry[1][iso]) for (_m, _d, w), entry
                    in zip(spec["indicators"], percentiles) if iso in entry[1]]
            held = sum(w for w, _ in have)
            # Record every indicator this country lacks whether or not it still
            # cleared the threshold. This used to sit in the else branch, which
            # made `missing` and `completeness` describe only the countries that
            # failed outright: a country holding 4 of economic resilience's 7
            # weight scored that criterion off 4 indicators and was still
            # reported at completeness 1.0, so the UI's partial-coverage badge
            # could never fire and the tooltip could never name a gap. Note the
            # threshold cuts both ways - a country that fails a criterion is not
            # ranked at all (see ranked_iso below) and lands in `unranked`, so
            # this branch is the only way a ranked row reports a shortfall.
            absent = [m for m, p in percentiles if iso not in p]
            if absent:
                missing[iso].update(absent)
            if held >= needed and have:
                scores[iso] = sum(w * v for w, v in have) / held
        criterion_scores[criterion_key] = scores

    # Axis 2 of 2. Raw km is the unit people reason in; the percentile is
    # there so the map legend can be scaled.
    distances = _isolation_km(scenario, countries)
    exposure_pct = _percentile_ranks([(iso, -km) for iso, km in distances.items()])

    total_indicators = sum(len(c["indicators"]) for c in CRITERIA.values())
    ranked_iso = [iso for iso in iso3_list
                  if all(iso in criterion_scores[c] for c in CRITERIA)]
    weight_sum = sum(scenario.weights.get(c, 0.0) for c in CRITERIA) or 1.0
    ordered_countries = sorted(
        (
            (
                sum(criterion_scores[c][iso] * scenario.weights.get(c, 0.0)
                    for c in CRITERIA) / weight_sum,
                iso,
            )
            for iso in ranked_iso
        ),
        reverse=True,
    )

    rows = []
    for idx, (resilience, iso) in enumerate(ordered_countries):
        have_count = total_indicators - len(
            [m for spec in CRITERIA.values() for m, _d, _w in spec["indicators"]
             if m in missing[iso]]
        )
        rows.append({
            "rank": idx + 1,
            "iso3": iso,
            "name": names.get(iso, iso),
            "structural_score": round(resilience, 1),
            "exposure_km": round(distances[iso]),
            "exposure_percentile": round(exposure_pct[iso], 1),
            "nuclear_armed": iso in NUCLEAR_ARMED,
            "belligerent": iso in scenario.belligerents,
            "ida_credit": iso in ida_credit,
            "criteria": {c: round(criterion_scores[c][iso], 1) for c in CRITERIA},
            "completeness": round(have_count / total_indicators, 2),
            # Named here too, not just on `unranked`: a ranked country can clear
            # every criterion's weight threshold and still be short an indicator,
            # and the UI tooltip lists them by name. Without this the field is
            # undefined for exactly the rows the UI offers it on.
            "missing": sorted(missing[iso]),
})


    return {
        "scenario": {
            "slug": scenario.slug, "name": scenario.name,
            "explanation": scenario.explanation, "not_measured": scenario.not_measured,
            "epicentres": [{"lat": a, "lon": b, "label": c} for a, b, c in scenario.epicentres],
            "belligerents": list(scenario.belligerents),
        },
        "criteria": {k: v["name"] for k, v in CRITERIA.items()},
        "weights": scenario.weights,
        "flags": {
            "nuclear_armed": {
                "label": "Nuclear-armed state",
                "basis": "Curated list of the nine states recognised as nuclear-armed under the NPT, cross-checked against SIPRI military expenditure. Reported only; never part of any score.",
            },
            "belligerent": {
                "label": "Party to this scenario",
                "basis": "Per-scenario, hand-declared. Reported only; never part of any score.",
            },
            "ida_credit": {
                "label": "IDA credit (fragility proxy)",
                "basis": "World Bank lending type. This is a poverty-and-creditworthiness signal, NOT a fragility classification: it omits conflict, institutional collapse and displacement, and misses fragile countries that are not IDA-eligible. The authoritative OECD DAC fragile-contexts list is not machine-readable (oecd.org returns HTTP 403 to non-browser clients, verified 2026-09-28) and CPIA is not in the public World Bank API.",
            },
        },
        "axes": {"structural": "Socio-economic and structural indicators only. Excludes proximity to conflict and nuclear posture, which are reported separately and never combined with it."},
        "countries_ranked": len(rows),
        "universe": len(iso3_list),
        # So the UI can say "scored on 20 of 22 indicators" without hardcoding
        # 22 in a tooltip, which is the kind of number that goes stale the next
        # time a criterion changes and nobody notices until it is wrong.
        "indicator_total": total_indicators,
        "ranked": rows,
        "unranked": [
            {
                "iso3": iso, "name": names.get(iso, iso),
                "missing": sorted(missing[iso]),
                "exposure_km": round(distances[iso]),
                "nuclear_armed": iso in NUCLEAR_ARMED,
                "belligerent": iso in scenario.belligerents,
                "ida_credit": iso in ida_credit,
            }
            for iso in iso3_list if iso not in set(ranked_iso)
        ],
    }
