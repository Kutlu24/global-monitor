# Risk Simulator - data-driven rewrite

## Why this exists

The original module (`frontend/src/lib/risk.ts`, ported from the standalone
`risk-simulator-pro` Streamlit app) scored **19 hand-picked countries** against
**11 criteria scored 0-10 by hand**, with no API and no ETL behind it. Two
consequences, both visible to users on 2026-09-28:

- The Russia-NATO Conflict map showed almost all of Europe as "no data"
  (grey). Poland, the Baltics, Ukraine, Germany, France and Turkey were not
  in the file at all - only 7 of ~43 European countries were.
- The "Vulnerable" tier contained exactly two European countries, Portugal
  and Italy, and only incidentally: they rank low on energy independence and
  demographics, which are true facts but have nothing to do with a
  Russia-NATO war. Finland - the single genuinely exposed European country
  present - ranked 17/19.

Root cause is coverage, not the arithmetic. The model also had no
exposure/proximity variable: `Geographic Isolation` was a fixed hand-scored
"is far from everyone" number, so a rich, stable country adjacent to a war
still ranked "Resilient".

Decision (2026-09-28): the model becomes **data-derived only**. The four
criteria with no source in World Bank/IMF/OECD/UNDP - `Nuclear Risk`,
`Political Neutrality`, `Public Preparedness`, `Cybersecurity` - are removed
rather than kept as judgment calls. Nuclear posture returns separately, as a
documented non-composite axis (see below).

## Sources

Three publishers, each carrying something the others do not. Verified
live 2026-09-28.

| Source | Endpoint | Carries | Coverage |
|---|---|---|---|
| World Bank | `api.worldbank.org/v2` (JSON) | 18 of 20 indicators | 211 countries |
| IMF WEO | `imf.org/external/datamapper/api/v1` | `GGXWDG_NGDP` general government gross debt | 226 |
| UNDP HDR | `hdr.undp.org` published CSV (no API - their Data API needs a manually-approved key) | `mys` mean years of schooling | 204 |

Neither non-WB series is a duplicate of a WDI one:

- **Debt** was dropped from the criteria because WDI `GC.DOD.TOTL.GD.ZS` covers
  3 of 7 countries tested, the gaps being Finland, Lithuania and Portugal -
  euro-area states reporting on a Maastricht basis. WEO covers all of them.
- **Schooling** was the one dimension with no indicator anywhere in the model.
  Income, health, employment, demographics, climate and energy were covered;
  education was not.

### Rejected after testing

- **IMF `BRASS_MI` reserves (months of imports)** - the ideal energy-security
  buffer, and not in WDI. Only 53 countries, so unusable for a 211-country
  universe.
- **OECD DAC fragile-contexts list** - `oecd.org` returns HTTP 403 to
  non-browser clients and the SDMX endpoint does not expose it. See
  "Known gaps".
- **UNDP HDI itself** - already ingested, but it is a composite of income,
  health and education, so adding it as a criterion would double-count all
  three.

## The six structural criteria

All six are computed from the three sources above. `direction`: `+1` higher is
more resilient, `-1` lower is more resilient, `0` two-sided (scored by
distance from the cross-country median). `weight` lets a level outweigh a
flow - see "Levels and flows" below.

These six are the **structural** axis only. Proximity to conflict and nuclear
posture are separate reported axes and are never added to this number.

| Criterion | Indicators (metric_id <- WB code) |
|---|---|
| Economic Resilience | `gdp_per_capita_ppp` <- NY.GDP.PCAP.PP.KD (+1, **w3**), `gdp_growth_3y_pct` <- NY.GDP.MKTP.KD.ZG (+1, w1), `govt_debt_pct_gdp` <- GGXWDG_NGDP (-1, w1), `industry_pct_gdp` <- NV.IND.TOTL.ZS (+1, w1), `current_account_pct_gdp` <- BN.CAB.XOKA.GD.ZS (0, w1) |
| Domestic Social Stability | `unemployment_pct` <- SL.UEM.TOTL.ZS (-1), `gini_index` <- SI.POV.GINI (-1), `poverty_headcount_pct` <- SI.POV.DDAY (-1), `female_labor_participation_pct` <- SL.FAM.WORK.FE.ZS (+1) |
| Human & Physical Infrastructure | `life_expectancy_years` (existing), `mean_years_schooling` <- UNDP `mys_2023` (+1), `health_exp_per_capita_usd` <- SH.XPD.CHEX.PC.CD (+1), `physicians_per_1000` <- SH.MED.PHYS.ZS (+1), `internet_users_pct` <- IT.NET.USER.ZS (+1) |
| Climate Resilience | `co2_per_capita_t` <- EN.GHG.CO2.PC.CE.AR5 (-1), `renewable_electricity_pct` <- EG.ELC.RNEW.ZS (+1), `forest_area_pct` <- AG.LND.FRST.ZS (+1) |
| Energy Independence | `fossil_fuel_energy_pct` <- EG.USE.COMM.FO.ZS (-1), `fuel_exports_pct` <- TX.VAL.FUEL.ZS.UN (+1) |
| Demographic Resilience | `age_dependency_pct` <- SP.POP.DPND (-1), `fertility_rate` <- SP.DYN.TFRT.IN (0), `population_growth_pct` <- SP.POP.GROW (0) |

`life_expectancy_years` already exists in the catalogue (social dimension) and
is reused rather than re-fetched.

### Deliberately excluded

- `GC.DOD.TOTL.GD.ZS` (central government debt % GDP): available for only 3 of
  7 countries tested, and the missing ones are Finland, Lithuania and Portugal
  - euro-area states report on a Maastricht basis. Dropping it rather than
  leaving a metric that is systematically absent for exactly the EU members
  this rewrite is about.
- `NY.GDP.NRES.RT.ZS` is not a valid WDI code (verified 2026-09-28; returns
  `Invalid value`). The valid equivalent is `NY.GDP.TOTL.RT.ZS`.

## Geographic Isolation is a separate axis, not a criterion

The old criterion was a fixed "is this country isolated" number, weighted 45%
in the Russia-NATO scenario. It is now **exposure**, reported in kilometres
alongside the structural score and never averaged into it.

Each scenario declares its epicentres as **coordinates of actual flashpoints**, not
country capitals, and exposure is `min(haversine(country, epicentre))` over
them.

For Russia-NATO the epicentres are Kaliningrad, the Belarus-Russia border,
Donetsk, the Suwalki Gap and the Finland-Russia border - not "Russia's capital".
This matters: with capital-to-capital distance the first prototype gave Poland,
Estonia, Latvia, Lithuania, Turkey and Ukraine all an identical `0 km`,
collapsing exactly the distinction the axis exists to draw.

**Why it can no longer be a criterion.** When proximity to a war was weighted
into a single number, Belarus ranked 3rd and Russia 6th on \"resilience\" -
because their GDP per capita, industry share and infrastructure really are
adequate, while the war sat in a separate, mostly ignored term. A reader saw
\"Belarus: Resilient\". Splitting the axes fixes the arithmetic; the
`belligerents` flag below fixes the reading.

## Reported-only flags

Two things cannot be derived from the data but are too important to omit. Both
are **flags, never scores**, and both are short documented lists:

- **`nuclear_armed`** - RUS, USA, CHN, GBR, FRA, IND, PAK, PRK, ISR. Only 8 of
  the 9 appear in the universe because PRK is not in the World Bank country
  list. Cross-checked at ingest against SIPRI `military_exp_pct_gdp`: a
  nuclear-armed state should sit in the upper tail of militarisation. A sanity
  check, not the source of truth.
- **`belligerent`** - per scenario. Russia-NATO declares RUS and BLR; China-US
  declares CHN and USA. Ukraine is a target, not a party, so it is deliberately
  absent. Same rationale as the nuclear list: a hand-maintained binary folded
  into a score would make the headline number non-reproducible, and it is
  reported next to the score instead.

## Levels and flows: why GDP growth carries weight 1

The first working version averaged `gdp_per_capita_ppp` (a stock) and
`gdp_growth_pct` (a rate) 1:1. Measured percentiles at that point:

| Country | GDP pc (pctile) | 2024 growth (pctile) | Result |
|---|---|---|---|
| Niger | 4 | **97** (8.3%) | economic resilience 43.6 |
| Mali | 10 | **80** (5.0%) | economic resilience 51.4 |
| Germany | 88 | **10** (-0.5%) | dragged down by one recession year |
| Norway | 97 | 24 (1.4%) | |

Niger is 4th-percentile on income and scored as mid-table, because poor
countries genuinely grow faster off a low base and a single year of that is a
huge number. Two changes:

1. Growth is stored as `gdp_growth_3y_pct`, the mean of the three most recent
   annual values. This removes single-year weather (Niger 2024 = 8.3% but the
   3-year mean is 7.7%; Germany 2024 = -0.5%, mean 0.15%). It does **not**
   remove the low-base effect - Niger is still at 7.7%.
2. GDP per capita carries weight 3, growth weight 1. The level dominates; the
   flow only breaks ties.

Result: Niger's economic resilience 43.6 -> **29.9** (overall rank 154/211),
Mali 51.4 -> 35.4, Germany back to 61.2. Note the same care applies to
`population_growth_pct` and `fertility_rate`, which are two-sided (scored by
distance from the median) precisely so that a poor fast-growing country is not
penalised for the one dimension that is going its way.

## Normalisation: percentile rank, not min-max

Each indicator is converted to its percentile across the full country universe
(ties averaged), then a criterion is the **weighted** mean of the indicators the
country actually has. Percentiles were chosen because:

- The tool is explicitly about *relative* standing under a scenario, not an
  absolute pass/fail score.
- Min-max is hostage to outliers (one extreme GDP-per-capita value would
  compress every other country into a narrow band) and would silently change
  every country's score whenever a country is added or removed.

### Partial coverage, on a stated threshold

A country needs **at least half of a criterion's total weight** to be scored on
it, and is scored on that criterion from whatever it has. `completeness` (the
share of all 20 indicators present) is returned per country, and every missing
indicator is named in the `unranked` list rather than dropped silently.

This replaced a stricter "every indicator of every criterion required" rule,
under which **112 of 211 countries scored** and the fragile states the user
asked about were nearly all excluded. Verified coverage improvements:

- `energy_imports_pct` (EG.IMP.CONS.ZS) was removed because it is a *trade-flow*
  identity, not an energy-security level: a net fuel **exporter** reports no
  value, so it was missing for exactly the countries under energy stress.
  Replaced by `fossil_fuel_energy_pct` (191 countries).
- `renewable_electricity_pct` moved from EG.FEC.RNEW.ZS to EG.ELC.RNEW.ZS, which
  has real coverage rather than a handful of reporting economies.
- All 12 fragile states in the sample set now rank: Afghanistan, Burkina Faso,
  Haiti, Libya, Mali, Niger, Sudan, South Sudan, Syria, Chad, Yemen.
  Previously only Niger ranked.

Current: **175 of 211 countries (82%)**. The 36 unranked are listed with their
specific missing indicators.

Two regressions worth naming, both consequences of adding indicators rather
than bugs: GDP per capita is missing for 15 countries and carries weight 3 of 7
in Economic Resilience, so those countries fail that criterion; and each added
indicator raises the per-criterion weight bar, so the ranked count moved 178 ->
175 when debt and schooling joined.

## Fragility: an IDA proxy, labelled as one

The user asked for fragile countries to be visible. The authoritative
classification is the OECD DAC annual fragile-contexts list and it is not
reachable: `oecd.org` returns **HTTP 403** to non-browser clients and the SDMX
endpoint does not expose it (both verified 2026-09-28). CPIA, the World Bank's
own fragility score, is IDA-only and genuinely not in the public API.

What is available is the World Bank's `lendingType`, already returned by the
country endpoint this module fetches. `fragility_proxy()` returns true for
`IDA` and deliberately excludes `Blend`.

**IDA credit is a poverty-and-creditworthiness signal, not a fragility
signal.** It says the Bank judged a country too poor or too credit-impaired
for ordinary IBRD terms. It does not capture conflict, institutional collapse
or displacement, and it misses fragile countries that are not IDA-eligible. The
51 countries it flags include Guyana (#35), Samoa (#66) and Sri Lanka (#99) -
countries with functioning states and no conflict. The API ships the label
**\"IDA credit (fragility proxy)\"** with that caveat attached, and the UI must
never render it as \"fragile\".

## Nuclear posture: separate axis, not blended

Restored on 2026-09-28 at the user's request, as a **parallel axis** that is
reported alongside the structural score and never mixed into it. See
"Reported-only flags" above for the list and the SIPRI cross-check.

Shown as its own labelled flag per country, so a reader can see "high
exposure, mid structural" (Poland) and "low exposure, high structural" (Norway)
side by side instead of having those two facts averaged into one number that
means neither.

**Stated limitation, shown on the page:** the Russia-NATO scenario does not
measure nuclear deterrence, alliance alignment, war losses or refugee flows.
None exist in the source data, so none are hand-scored. The page says so rather
than implying otherwise under a "Russia-NATO Conflict" heading.

## Naming: why the axis is "structural", not "resilience"

The first two-axis version still called the number `resilience_score` and
`tier_label: "Resilient"`, which is the exact reading that started this
rewrite - Ukraine ranked 17th and read "Resilient" in a war it is fighting.
"Resilience" is a verdict; "structural" names what is actually measured.
There is no `tier` field and no `Resilient`/`Vulnerable` label anywhere in the
output.

## Scenarios

Six scenarios are kept. Weights are set deliberately per scenario and sum to
1.00 across the six structural criteria; exposure is no longer a weighted term
in any of them. Equal weighting was tested in the prototype and produces
defensible-but-absurd results (Peru, Colombia, Ecuador and Myanmar in the
global top 8 for Russia-NATO, on low age-dependency and high forest share).

Each scenario carries: `weights` over the six structural criteria, `epicentres`,
`belligerents`, and an `explanation` that states what the scenario does and does
not measure. The Hormuz scenario's explanation previously said isolation was
"deliberately weighted 0", which stopped being true when exposure became a
separate axis; all six explanations were re-checked for stale claims on
2026-09-28.

## Engineering constraints discovered during the prototype

- **World Bank throttles hard.** Rapid successive calls return near-empty
  bodies: `IT.NET.USER.ZS` returned 221 countries once and 39 on the next run,
  and one run returned 1-9 countries for most indicators. The ingestion must
  use exponential backoff, on-disk caching, and a **coverage assertion** that
  raises rather than proceeding.
- **Never pass `mrv=1`.** Already documented in `worldbank.py`, rediscovered
  here: it caps coverage badly. Use a year window and reduce to
  latest-non-null locally.
- **Never pass `MRV=1` (uppercase) with a `date` range** - that combination
  also collapsed coverage in the prototype.
- A silent empty response produced **0 scored countries** with no error
  raised. Every fetch must assert non-trivial coverage.

## Schema changes required

`countries` currently held only `(iso3, name)` and `observations.iso3`
references it, so no country outside the bloc set could be stored. Added:

- `countries`: `latitude`, `longitude`, `income_level`, `region`
  (all sourced from the World Bank country endpoint, which already returns
  them; 211 of 217 real countries have coordinates). Added as a nullable-column
  migration so existing databases upgrade in place.
- `risk_scenarios`: scenario -> weights, epicentres, belligerents, explanation.
  Held in code (`risk.py`), not in a table - the six scenarios are editorial
  content, and a table would only split the definition across two places.
- Risk scores are **computed, never stored**, and recomputed per request.

## Known gaps

These are real and deliberately not papered over:

- **The OECD is not represented.** Its fragile-contexts list is the one
  authoritative source this model cannot reach (403), and it carries no
  numeric indicator that WDI or WEO lack. Everything else the user asked for -
  World Bank, IMF and UNDP - is now wired in.
- **Fragility is a proxy, not a classification.** See the section above. A real
  classification means hand-typing the DAC list with a year and a citation,
  refreshed annually by hand, with no way to detect that it has been superseded.
  That is the same maintenance shape as the nuclear list, and defensible if
  the accuracy is worth it - but it is a decision, not a default.
- **Throttling is managed by a freshness gate, not by a cache.** There is no
  separate cache layer, and there does not need to be one: the Docker named
  volume `global_monitor_data` already holds the SQLite database across
  restarts, so the previous run's observations persist. What was missing was
  anything *reading* that persisted data before re-fetching. `db.metrics_fetched_within()`
  compares `MAX(fetched_at)` for all 23 risk metrics against a 30-day window
  and `run_source("worldbank_risk")` skips its ~120-request pull when they are
  all fresh, dropping a repeat `ingest all` from ~120 requests to 0.3 s.

  Two details that matter: it reads `fetched_at` (when *we* last checked) and
  not `period` (what the source calls the figure) - `period` reads "2024"
  forever, so gating on it would re-fetch on every boot and call itself stale
  permanently. And it is all-or-nothing across the metric set, so a run
  interrupted halfway is treated as stale and the next run repairs it rather
  than cementing the gap.

  The country-universe seed (1 request) deliberately still runs on every boot,
  so a newly-listed World Bank country appears immediately. It just has no
  observations until the next refresh, so it renders as unranked rather than
  missing.

  `worldbank_risk` also gained a **monthly** scheduler job. It used to be
  reachable only from the entrypoint's unconditional `ingest all`, i.e. it
  refreshed on container restarts and on no schedule at all. Monthly is far
  more often than WDI, WEO or HDR can actually change.

## Country universe

All World Bank countries with coordinates: **211** (of 217 real entries).
This includes all 29 of EU-27 + UK + Turkey, and the fragile states the user
asked about, without any hand-picked allowlist.
