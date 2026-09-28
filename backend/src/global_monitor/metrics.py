"""The metric catalog - one row per tracked indicator, seeded here and
read by aggregate.py (for default_aggregation/weight_metric_id) and the
frontend's build-time API calls (for display name/unit/license/source, and
schema.org Dataset markup).

Ratio/index metrics (military-exp-%-GDP, trade-%-GDP, HDI, life expectancy,
enrollment) use `weighted_mean` rather than a naive average across members -
weighted by the metric that makes the ratio meaningful at bloc scale: GDP
for %-of-GDP ratios (so the bloc figure reflects "total X / total GDP", not
an unweighted average that treats a tiny economy the same as a huge one),
population for per-capita/human-development metrics.
"""
from __future__ import annotations

from . import db
from .models import Metric

METRICS = [
    Metric(
        metric_id="gdp_current_usd", dimension="economic", name="GDP (current US$)", unit="USD",
        source="world_bank", source_dataset_code="NY.GDP.MKTP.CD", license="CC BY-4.0",
        update_cadence="annual", default_aggregation="sum",
    ),
    Metric(
        metric_id="population_total", dimension="social", name="Population, total", unit="people",
        source="world_bank", source_dataset_code="SP.POP.TOTL", license="CC BY-4.0",
        update_cadence="annual", default_aggregation="sum",
    ),
    Metric(
        metric_id="military_exp_pct_gdp", dimension="military", name="Military expenditure (% of GDP)",
        unit="% of GDP", source="world_bank", source_dataset_code="MS.MIL.XPND.GD.ZS", license="CC BY-4.0",
        update_cadence="annual", default_aggregation="weighted_mean", weight_metric_id="gdp_current_usd",
    ),
    Metric(
        metric_id="trade_pct_gdp", dimension="trade", name="Trade (% of GDP)", unit="% of GDP",
        source="world_bank", source_dataset_code="NE.TRD.GNFS.ZS", license="CC BY-4.0",
        update_cadence="annual", default_aggregation="weighted_mean", weight_metric_id="gdp_current_usd",
    ),
    Metric(
        metric_id="life_expectancy_years", dimension="social", name="Life expectancy at birth",
        unit="years", source="world_bank", source_dataset_code="SP.DYN.LE00.IN", license="CC BY-4.0",
        update_cadence="annual", default_aggregation="weighted_mean", weight_metric_id="population_total",
    ),
    Metric(
        metric_id="secondary_enrollment_pct", dimension="social", name="Secondary school enrollment (% gross)",
        unit="%", source="world_bank", source_dataset_code="SE.SEC.ENRR", license="CC BY-4.0",
        update_cadence="annual", default_aggregation="weighted_mean", weight_metric_id="population_total",
    ),
    Metric(
        metric_id="hdi", dimension="social", name="Human Development Index", unit="index (0-1)",
        source="undp", source_dataset_code=None, license="CC BY-3.0 IGO",
        update_cadence="annual", default_aggregation="weighted_mean", weight_metric_id="population_total",
    ),
    Metric(
        metric_id="mean_years_schooling", dimension="social", name="Mean years of schooling", unit="years",
        source="undp", source_dataset_code="mys", license="CC BY-3.0 IGO",
        update_cadence="annual", default_aggregation="weighted_mean", weight_metric_id="population_total",
    ),
    Metric(
        # Added 2026-09-28. The World Bank WDI series for government debt
        # (GC.DOD.TOTL.GD.ZS) covers 3 of the 7 countries tested, the missing
        # ones being euro-area states reporting on a Maastricht basis, so debt
        # had been dropped from the risk criteria. WEO covers 226 countries.
        metric_id="govt_debt_pct_gdp", dimension="economic",
        name="General government gross debt", unit="% of GDP",
        source="imf_weo", source_dataset_code="GGXWDG_NGDP",
        license="IMF terms of use (free, non-commercial)",
        update_cadence="annual", default_aggregation="weighted_mean",
        weight_metric_id="gdp_current_usd",
    ),
    Metric(
        metric_id="military_exp_usd", dimension="military", name="Military expenditure (current US$)",
        unit="USD", source="sipri", source_dataset_code=None, license="SIPRI terms of use",
        update_cadence="annual", default_aggregation="sum",
    ),
    Metric(
        metric_id="trade_exports_world_usd", dimension="trade", name="Exports to the world",
        unit="USD", source="un_comtrade", source_dataset_code=None, license="UN Comtrade terms of use",
        update_cadence="annual", default_aggregation="sum",
    ),
    Metric(
        metric_id="trade_imports_world_usd", dimension="trade", name="Imports from the world",
        unit="USD", source="un_comtrade", source_dataset_code=None, license="UN Comtrade terms of use",
        update_cadence="annual", default_aggregation="sum",
    ),
    # Intra-bloc trade metrics are NOT aggregated from `observations` (no
    # single country "has" an intra-bloc value) - aggregate.py computes
    # them directly from bloc_trade_flows instead. Still cataloged here so
    # the frontend/schema.org layer has a name/unit/license for them.
    Metric(
        metric_id="trade_intra_bloc_exports_usd", dimension="trade", name="Intra-bloc exports",
        unit="USD", source="un_comtrade", source_dataset_code=None, license="UN Comtrade terms of use",
        update_cadence="annual", default_aggregation="sum",
    ),
]

# Risk-simulator criteria inputs - see docs/risk-model.md for the full
# derivation and for the two indicators deliberately left out
# (GC.DOD.TOTL.GD.ZS is systematically missing for euro-area states;
# NY.GDP.NRES.RT.ZS is not a valid WDI code at all).
#
# These are NOT aggregated into bloc averages. They are read per-country by
# risk.py to build percentile ranks, so their default_aggregation is only a
# fallback for the generic aggregate.py path. Life expectancy is the one
# exception: it is already cataloged above for the social dimension and is
# reused by the Infrastructure & Health criterion rather than duplicated.
#
# Climate metrics sit under "economic" because the dimension set is a closed
# CHECK constraint (economic/trade/social/military) and none of them means
# "environmental"; they are resource-endowment measures, and grouping them
# with the other physical-economy inputs is the least misleading fit.
RISK_INPUT_METRICS = [
    # Economic Resilience
    Metric(metric_id="gdp_per_capita_ppp", dimension="economic", name="GDP per capita, PPP (constant intl $)",
           unit="intl $", source="world_bank", source_dataset_code="NY.GDP.PCAP.PP.KD", license="CC BY-4.0",
           update_cadence="annual", default_aggregation="weighted_mean", weight_metric_id="population_total"),
    Metric(metric_id="gdp_growth_3y_pct", dimension="economic", name="Real GDP growth, 3-year mean", unit="%",
           source="world_bank", source_dataset_code="NY.GDP.MKTP.KD.ZG", license="CC BY-4.0",
           update_cadence="annual", default_aggregation="weighted_mean", weight_metric_id="gdp_current_usd"),
    Metric(metric_id="industry_pct_gdp", dimension="economic", name="Industry (incl. construction), value added",
           unit="% of GDP", source="world_bank", source_dataset_code="NV.IND.TOTL.ZS", license="CC BY-4.0",
           update_cadence="annual", default_aggregation="weighted_mean", weight_metric_id="gdp_current_usd"),
    Metric(metric_id="current_account_pct_gdp", dimension="economic", name="Current account balance",
           unit="% of GDP", source="world_bank", source_dataset_code="BN.CAB.XOKA.GD.ZS", license="CC BY-4.0",
           update_cadence="annual", default_aggregation="weighted_mean", weight_metric_id="gdp_current_usd"),
    # Domestic Social Stability
    Metric(metric_id="unemployment_pct", dimension="social", name="Unemployment, total (% of labour force)",
           unit="%", source="world_bank", source_dataset_code="SL.UEM.TOTL.ZS", license="CC BY-4.0",
           update_cadence="annual", default_aggregation="weighted_mean", weight_metric_id="population_total"),
    Metric(metric_id="gini_index", dimension="social", name="Gini index", unit="index (0-100)",
           source="world_bank", source_dataset_code="SI.POV.GINI", license="CC BY-4.0",
           update_cadence="annual", default_aggregation="mean"),
    Metric(metric_id="poverty_headcount_pct", dimension="social", name="Poverty headcount at $3.65/day",
           unit="% of population", source="world_bank", source_dataset_code="SI.POV.DDAY", license="CC BY-4.0",
           update_cadence="annual", default_aggregation="weighted_mean", weight_metric_id="population_total"),
    Metric(metric_id="female_labor_participation_pct", dimension="social",
           name="Female labour force participation", unit="% of female population 15+",
           source="world_bank", source_dataset_code="SL.FAM.WORK.FE.ZS", license="CC BY-4.0",
           update_cadence="annual", default_aggregation="weighted_mean", weight_metric_id="population_total"),
    # Infrastructure & Health
    Metric(metric_id="health_exp_per_capita_usd", dimension="social", name="Health expenditure per capita",
           unit="current US$", source="world_bank", source_dataset_code="SH.XPD.CHEX.PC.CD", license="CC BY-4.0",
           update_cadence="annual", default_aggregation="weighted_mean", weight_metric_id="population_total"),
    Metric(metric_id="physicians_per_1000", dimension="social", name="Physicians per 1,000 people",
           unit="per 1,000", source="world_bank", source_dataset_code="SH.MED.PHYS.ZS", license="CC BY-4.0",
           update_cadence="annual", default_aggregation="weighted_mean", weight_metric_id="population_total"),
    Metric(metric_id="internet_users_pct", dimension="social", name="Individuals using the Internet",
           unit="% of population", source="world_bank", source_dataset_code="IT.NET.USER.ZS", license="CC BY-4.0",
           update_cadence="annual", default_aggregation="mean"),
    # Climate Resilience
    Metric(metric_id="co2_per_capita_t", dimension="economic", name="CO2 emissions per capita",
           unit="t CO2/capita", source="world_bank", source_dataset_code="EN.GHG.CO2.PC.CE.AR5", license="CC BY-4.0",
           update_cadence="annual", default_aggregation="weighted_mean", weight_metric_id="population_total"),
    # EG.ELC.RNEW.ZS rather than EG.FEC.RNEW.ZS ("renewable electricity output"
    # vs "renewable electricity output % of total"): same idea, 250 countries
    # covered instead of 69 in the ingest window (verified 2026-09-28).
    Metric(metric_id="renewable_electricity_pct", dimension="economic",
           name="Renewable electricity output", unit="% of total electricity output",
           source="world_bank", source_dataset_code="EG.ELC.RNEW.ZS", license="CC BY-4.0",
           update_cadence="annual", default_aggregation="mean"),
    Metric(metric_id="forest_area_pct", dimension="economic", name="Forest area", unit="% of land area",
           source="world_bank", source_dataset_code="AG.LND.FRST.ZS", license="CC BY-4.0",
           update_cadence="annual", default_aggregation="mean"),
    # Energy Independence
    # Fossil-fuel share of energy use instead of EG.IMP.CONS.ZS (net energy
    # imports % of use): better coverage (191 vs 185 countries) and it measures
    # the thing the criterion actually cares about - exposure to a supply cut.
    # "Net importer" is a trade-flow identity, which is why it was missing for
    # exactly the energy-poor countries that are most exposed to a shock.
    Metric(metric_id="fossil_fuel_energy_pct", dimension="economic",
           name="Fossil fuel energy consumption", unit="% of total energy use",
           source="world_bank", source_dataset_code="EG.USE.COMM.FO.ZS", license="CC BY-4.0",
           update_cadence="annual", default_aggregation="mean"),
    Metric(metric_id="fuel_exports_pct", dimension="trade", name="Fuel exports",
           unit="% of merchandise exports", source="world_bank", source_dataset_code="TX.VAL.FUEL.ZS.UN",
           license="CC BY-4.0", update_cadence="annual", default_aggregation="mean"),
    # Demographic Resilience
    Metric(metric_id="age_dependency_pct", dimension="social", name="Age dependency ratio",
           unit="% of working-age population", source="world_bank", source_dataset_code="SP.POP.DPND",
           license="CC BY-4.0", update_cadence="annual", default_aggregation="mean"),
    Metric(metric_id="fertility_rate", dimension="social", name="Fertility rate, total",
           unit="births per woman", source="world_bank", source_dataset_code="SP.DYN.TFRT.IN", license="CC BY-4.0",
           update_cadence="annual", default_aggregation="mean"),
    Metric(metric_id="population_growth_pct", dimension="social", name="Population growth",
           unit="% annual", source="world_bank", source_dataset_code="SP.POP.GROW", license="CC BY-4.0",
           update_cadence="annual", default_aggregation="mean"),
]

METRICS = METRICS + RISK_INPUT_METRICS


def seed() -> None:
    for metric in METRICS:
        db.upsert_metric(metric)
