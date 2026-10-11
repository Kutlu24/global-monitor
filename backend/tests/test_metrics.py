"""metrics.py: the metric catalog. aggregate.py trusts these rows blindly
(default_aggregation, weight_metric_id), so catalog mistakes surface as wrong
numbers, not as errors."""
from collections import Counter

from global_monitor import db, metrics

_DIMENSIONS = {"economic", "trade", "social", "military"}
_AGGREGATIONS = {"sum", "mean", "weighted_mean"}
_CADENCES = {"continuous", "quarterly", "annual"}


def test_metric_ids_are_unique():
    dupes = [m for m, n in Counter(x.metric_id for x in metrics.METRICS).items() if n > 1]
    assert dupes == []


def test_enumerated_fields_are_valid():
    for m in metrics.METRICS:
        assert m.dimension in _DIMENSIONS, m.metric_id
        assert m.default_aggregation in _AGGREGATIONS, m.metric_id
        assert m.update_cadence in _CADENCES, m.metric_id


def test_weighted_mean_metrics_declare_an_existing_weight_metric():
    ids = {m.metric_id for m in metrics.METRICS}
    for m in metrics.METRICS:
        if m.default_aggregation == "weighted_mean":
            assert m.weight_metric_id, f"{m.metric_id} is weighted_mean without a weight"
            assert m.weight_metric_id in ids, f"{m.metric_id} weights by unknown {m.weight_metric_id}"


def test_weight_metrics_are_summable_not_ratios():
    by_id = {m.metric_id: m for m in metrics.METRICS}
    for m in metrics.METRICS:
        if m.weight_metric_id:
            assert by_id[m.weight_metric_id].default_aggregation == "sum"


def test_every_metric_cites_source_and_license():
    for m in metrics.METRICS:
        assert m.source and m.license, m.metric_id


def test_seed_satisfies_database_check_constraints(seeded):
    # the schema has CHECK constraints on dimension/cadence/aggregation
    assert {m.metric_id for m in db.get_metrics()} == {m.metric_id for m in metrics.METRICS}
