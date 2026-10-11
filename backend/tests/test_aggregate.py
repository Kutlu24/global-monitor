"""aggregate.py: country observations -> bloc aggregates. The business rules
that matter: missing values are skipped (never imputed), member_count tells
the truth about coverage, weights use the latest known value, and
single-country blocs get an explicit NULL for intra-bloc trade."""
import pytest

from global_monitor import aggregate, db
from global_monitor.models import BlocTradeFlow, Metric


def _metric(metric_id: str) -> Metric:
    return next(m for m in db.get_metrics() if m.metric_id == metric_id)


def test_sum_adds_members_per_period(seeded, obs):
    obs("gdp_current_usd", {"USA": ("2023", 100.0), "CAN": ("2023", 20.0), "MEX": ("2023", 10.0)})
    aggregate.aggregate_metric("usmca", _metric("gdp_current_usd"))
    agg = db.latest_bloc_aggregate("usmca", "gdp_current_usd")
    assert (agg.period, agg.value, agg.member_count) == ("2023", 130.0, 3)


def test_missing_value_is_skipped_and_reflected_in_member_count(seeded, obs):
    obs("gdp_current_usd", {"USA": ("2023", 100.0), "CAN": ("2023", None), "MEX": ("2023", 10.0)})
    aggregate.aggregate_metric("usmca", _metric("gdp_current_usd"))
    agg = db.latest_bloc_aggregate("usmca", "gdp_current_usd")
    assert (agg.value, agg.member_count) == (110.0, 2)


def test_non_members_are_ignored(seeded, obs):
    obs("gdp_current_usd", {"USA": ("2023", 100.0), "JPN": ("2023", 9999.0)})
    aggregate.aggregate_metric("usmca", _metric("gdp_current_usd"))
    assert db.latest_bloc_aggregate("usmca", "gdp_current_usd").value == 100.0


def test_members_reporting_different_periods_are_bucketed_separately(seeded, obs):
    obs("gdp_current_usd", {"USA": ("2024", 100.0), "CAN": ("2023", 20.0)})
    aggregate.aggregate_metric("usmca", _metric("gdp_current_usd"))
    got = {a.period: (a.value, a.member_count) for a in db.get_bloc_aggregates("usmca") if a.metric_id == "gdp_current_usd"}
    assert got == {"2024": (100.0, 1), "2023": (20.0, 1)}


def test_weighted_mean_uses_weights(seeded, obs):
    obs("hdi", {"USA": ("2023", 0.9), "CAN": ("2023", 0.8)})
    obs("population_total", {"USA": ("2025", 300.0), "CAN": ("2025", 100.0)})
    aggregate.aggregate_metric("usmca", _metric("hdi"))
    agg = db.latest_bloc_aggregate("usmca", "hdi")
    assert agg.value == pytest.approx((0.9 * 300 + 0.8 * 100) / 400)
    assert agg.member_count == 2


def test_weight_uses_latest_period_not_exact_period_match(seeded, obs):
    # regression for the 2026-09-27 bug: metric period 2023, weight only 2025
    obs("hdi", {"USA": ("2023", 0.9)})
    obs("population_total", {"USA": ("2025", 330.0)})
    aggregate.aggregate_metric("us", _metric("hdi"))
    assert db.latest_bloc_aggregate("us", "hdi").value == pytest.approx(0.9)


def test_country_without_any_weight_is_excluded(seeded, obs):
    obs("hdi", {"USA": ("2023", 0.9), "CAN": ("2023", 0.1)})
    obs("population_total", {"USA": ("2025", 300.0)})  # CAN has no population at all
    aggregate.aggregate_metric("usmca", _metric("hdi"))
    agg = db.latest_bloc_aggregate("usmca", "hdi")
    assert agg.value == pytest.approx(0.9)
    assert agg.member_count == 1


def test_zero_weight_is_excluded(seeded, obs):
    obs("hdi", {"USA": ("2023", 0.9), "CAN": ("2023", 0.1)})
    obs("population_total", {"USA": ("2025", 300.0), "CAN": ("2025", 0.0)})
    aggregate.aggregate_metric("usmca", _metric("hdi"))
    assert db.latest_bloc_aggregate("usmca", "hdi").member_count == 1


def test_weighted_mean_without_weight_metric_raises(seeded):
    bad = Metric("x", "economic", "x", "u", "s", None, None, "annual", "weighted_mean", None)
    with pytest.raises(ValueError, match="weight_metric_id"):
        aggregate.aggregate_metric("eu", bad)


def test_unimplemented_aggregation_is_loud_not_silent(seeded):
    bogus = Metric("m", "economic", "m", "u", "s", None, None, "annual", "median")  # not a real mode
    with pytest.raises(NotImplementedError):
        aggregate.aggregate_metric("eu", bogus)


def test_single_country_bloc_gets_explicit_null_for_intra_bloc_trade(seeded):
    aggregate.aggregate_metric("us", _metric("trade_intra_bloc_exports_usd"))
    agg = db.latest_bloc_aggregate("us", "trade_intra_bloc_exports_usd")
    assert agg.value is None and agg.member_count == 0


def test_intra_bloc_trade_sums_flows(seeded):
    f = lambda rep, par, v: BlocTradeFlow("usmca", rep, par, "trade_intra_bloc_exports_usd", "2023", v, db.now())
    db.upsert_trade_flows([f("USA", "CAN", 5.0), f("CAN", "USA", 7.0), f("MEX", "USA", None)])
    aggregate.aggregate_metric("usmca", _metric("trade_intra_bloc_exports_usd"))
    agg = db.latest_bloc_aggregate("usmca", "trade_intra_bloc_exports_usd")
    assert (agg.value, agg.member_count) == (12.0, 2)


def test_aggregate_all_is_idempotent(seeded, obs):
    obs("gdp_current_usd", {"USA": ("2023", 100.0)})
    aggregate.aggregate_all()
    first = db.latest_bloc_aggregate("us", "gdp_current_usd").value
    aggregate.aggregate_all()
    assert db.latest_bloc_aggregate("us", "gdp_current_usd").value == first


def test_every_catalog_aggregation_kind_is_implemented_by_aggregate_metric(seeded):
    """Guards the pipeline: aggregate_all() runs over the whole catalog, so a
    metric whose default_aggregation aggregate.py can't handle aborts the run.
    """
    unimplemented = {m.default_aggregation for m in db.get_metrics()} - {"sum", "mean", "weighted_mean"}
    assert unimplemented == set(), f"aggregate.py cannot handle: {unimplemented}"


def test_mean_is_unweighted_and_reports_coverage(seeded, obs):
    mean_metric = next(m for m in db.get_metrics() if m.default_aggregation == "mean")
    obs(mean_metric.metric_id, {"USA": ("2023", 10.0), "CAN": ("2023", 20.0)})   # MEX missing
    aggregate.aggregate_metric("usmca", mean_metric)
    agg = db.latest_bloc_aggregate("usmca", mean_metric.metric_id)
    assert agg.value == pytest.approx(15.0) and agg.member_count == 2
