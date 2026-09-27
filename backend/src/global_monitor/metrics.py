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


def seed() -> None:
    for metric in METRICS:
        db.upsert_metric(metric)
