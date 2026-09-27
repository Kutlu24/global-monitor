"""The metric catalog - one row per tracked indicator, seeded here and
read by aggregate.py (for default_aggregation/weight_metric_id) and the
frontend's build-time API calls (for display name/unit/license/source, and
schema.org Dataset markup). Milestone 1 scope: GDP + population only.
Remaining metrics (trade, social, military) land in Milestone 2."""
from __future__ import annotations

from . import db
from .models import Metric

METRICS = [
    Metric(
        metric_id="gdp_current_usd",
        dimension="economic",
        name="GDP (current US$)",
        unit="USD",
        source="world_bank",
        source_dataset_code="NY.GDP.MKTP.CD",
        license="CC BY-4.0",
        update_cadence="annual",
        default_aggregation="sum",
    ),
    Metric(
        metric_id="population_total",
        dimension="social",
        name="Population, total",
        unit="people",
        source="world_bank",
        source_dataset_code="SP.POP.TOTL",
        license="CC BY-4.0",
        update_cadence="annual",
        default_aggregation="sum",
    ),
]


def seed() -> None:
    for metric in METRICS:
        db.upsert_metric(metric)
