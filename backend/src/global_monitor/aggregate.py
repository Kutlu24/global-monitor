"""Country-level observations -> bloc-level aggregates. Never hand-writes
bloc_aggregates rows - always derived from observations + bloc_membership,
so re-running this after new data lands is always safe and idempotent.

Milestone 1 scope: `sum` aggregation only (correct for GDP/population).
`weighted_mean` (for ratio/index metrics like HDI, weighted by population)
lands in Milestone 2 alongside the metrics that need it.
"""
from __future__ import annotations

from collections import defaultdict

from . import db
from .models import BlocAggregate, Metric


def _aggregate_sum(iso3_list: list[str], metric_id: str) -> list[tuple[str, float, int]]:
    """Returns (period, summed_value, member_count) for every period any
    member has data for - a bloc's members don't all report the same
    latest year, so this buckets by whatever period each observation
    actually is, rather than assuming one shared "current" period."""
    observations = db.get_observations(metric_id, iso3_list)
    by_period: dict[str, list[float]] = defaultdict(list)
    for obs in observations:
        if obs.value is not None:
            by_period[obs.period].append(obs.value)
    return [(period, sum(values), len(values)) for period, values in by_period.items()]


def aggregate_metric(bloc_id: str, metric: Metric) -> None:
    members = db.get_current_members(bloc_id)
    if not members:
        return
    if metric.default_aggregation == "sum":
        results = _aggregate_sum(members, metric.metric_id)
    else:
        # weighted_mean / mean land in Milestone 2 with the metrics that need them.
        raise NotImplementedError(
            f"default_aggregation={metric.default_aggregation!r} not yet implemented "
            f"(metric={metric.metric_id!r}) - Milestone 1 only covers sum-aggregated metrics."
        )
    computed_at = db.now()
    for period, value, member_count in results:
        db.upsert_bloc_aggregate(
            BlocAggregate(bloc_id=bloc_id, metric_id=metric.metric_id, period=period,
                           value=value, member_count=member_count, computed_at=computed_at)
        )


def aggregate_all() -> None:
    blocs = db.get_blocs()
    metrics = db.get_metrics()
    for bloc in blocs:
        for metric in metrics:
            if metric.default_aggregation != "sum":
                continue  # Milestone 2
            aggregate_metric(bloc.bloc_id, metric)
