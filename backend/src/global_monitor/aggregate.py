"""Country-level observations -> bloc-level aggregates. Never hand-writes
bloc_aggregates rows - always derived from observations/bloc_trade_flows +
bloc_membership, so re-running this after new data lands is always safe
and idempotent.
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


def _aggregate_weighted_mean(
    iso3_list: list[str], metric_id: str, weight_metric_id: str
) -> list[tuple[str, float, int]]:
    """weighted_mean = sum(value_i * weight_i) / sum(weight_i). The weight
    (population) uses each country's LATEST known value regardless of
    period, not an exact-period match against the metric's own period.

    Confirmed live (2026-09-27): requiring an exact period match meant
    HDI/life-expectancy/secondary-enrollment/military-%-GDP - all reported
    by their sources for 2023/2024 - could NEVER match population, which is
    only ever fetched for the current/latest year (2025) - producing an
    empty aggregate (silent N/A) for these metrics on EVERY bloc, not just
    one. Population changes slowly year to year, so weighting a
    slightly-older metric by the latest known population is a reasonable
    approximation - certainly better than no aggregate at all. A country
    still missing the weight metric ENTIRELY (any period) is excluded, per
    member_count's whole point (transparency about coverage, never silent
    interpolation) - this only relaxes the PERIOD requirement, not the
    presence requirement.
    """
    values = db.get_observations(metric_id, iso3_list)
    by_period: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for obs in values:
        if obs.value is None:
            continue
        weight_obs = db.latest_observation(obs.iso3, weight_metric_id)
        if weight_obs is not None and weight_obs.value is not None and weight_obs.value > 0:
            by_period[obs.period].append((obs.value, weight_obs.value))

    results = []
    for period, pairs in by_period.items():
        total_weight = sum(w for _, w in pairs)
        weighted_value = sum(v * w for v, w in pairs) / total_weight
        results.append((period, weighted_value, len(pairs)))
    return results


def _aggregate_intra_bloc_trade(bloc_id: str, metric_id: str) -> list[tuple[str, float | None, int]]:
    """Sums bloc_trade_flows for this bloc/metric. A single-country bloc
    (e.g. "us") has no possible intra-bloc pairs by construction - returns
    an explicit NULL/0-member row rather than silently omitting the metric,
    so the frontend can render "N/A (single-country bloc)" instead of a
    misleading blank."""
    members = db.get_current_members(bloc_id)
    if len(members) < 2:
        return [(db.now()[:10], None, 0)]
    flows = db.get_trade_flows(bloc_id, metric_id)
    by_period: dict[str, list[float]] = defaultdict(list)
    for flow in flows:
        if flow.value is not None:
            by_period[flow.period].append(flow.value)
    if not by_period:
        return []
    return [(period, sum(values), len(values)) for period, values in by_period.items()]


def aggregate_metric(bloc_id: str, metric: Metric) -> None:
    members = db.get_current_members(bloc_id)
    if not members:
        return

    if metric.metric_id == "trade_intra_bloc_exports_usd":
        results = _aggregate_intra_bloc_trade(bloc_id, metric.metric_id)
    elif metric.default_aggregation == "sum":
        results = _aggregate_sum(members, metric.metric_id)
    elif metric.default_aggregation == "weighted_mean":
        if not metric.weight_metric_id:
            raise ValueError(f"metric {metric.metric_id!r} is weighted_mean but has no weight_metric_id")
        results = _aggregate_weighted_mean(members, metric.metric_id, metric.weight_metric_id)
    else:
        raise NotImplementedError(f"default_aggregation={metric.default_aggregation!r} not implemented")

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
            aggregate_metric(bloc.bloc_id, metric)
