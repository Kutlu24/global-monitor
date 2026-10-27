"""verify_synthesis.py: the numeric grounding audit of LLM paragraphs. Uses
real bloc aggregates in a throwaway DB; no LLM and no network."""
from global_monitor import db, verify_synthesis as vs
from global_monitor.models import BlocAggregate, SynthesisText


def _agg(bloc_id, metric_id, value, period="2025"):
    db.upsert_bloc_aggregate(BlocAggregate(bloc_id, metric_id, period, value, 3, "2026-01-01T00:00:00+00:00"))


def _verdicts(text, page_key="bloc:eu"):
    row = SynthesisText(page_key=page_key, text=text, data_hash="x", generated_at="", provider="t", model="t")
    return {n.text: n.verdict for n in vs.verify_page(row).numbers}


def test_rounded_figures_are_grounded(seeded):
    _agg("eu", "gdp_current_usd", 21.243e12)
    _agg("eu", "military_exp_pct_gdp", 2.1794)
    got = _verdicts("The EU has a GDP of $21.24 trillion and spends 2.18% of GDP on defence (2025).")
    assert got["$21.24 trillion"] == "grounded"
    assert got["2.18%"] == "grounded"
    assert got["2025"] == "year"


def test_dropped_digit_group_is_a_magnitude_error(seeded):
    _agg("eu", "military_exp_usd", 460.556e9)
    assert _verdicts("The EU spends $4.606 billion on its military.")["$4.606 billion"] == "magnitude_error"


def test_invented_figure_is_ungrounded(seeded):
    _agg("eu", "gdp_current_usd", 21.243e12)
    assert _verdicts("GDP is $17.9 trillion.")["$17.9 trillion"] == "ungrounded"


def test_negative_figure_matches_by_magnitude(seeded):
    _agg("us", "current_account_pct_gdp", -4.0456)
    assert _verdicts("The current account balance is -4.05% of GDP.", "bloc:us")["4.05%"] == "grounded"


def test_ratio_of_two_blocs_is_derived(seeded):
    _agg("eu", "military_exp_usd", 460e9)
    _agg("us", "military_exp_usd", 920e9)
    got = _verdicts("The US spends 2 times as much as the EU.", "compare:eu-vs-us:military")
    assert got["2"] in ("derived", "incidental")


def test_broken_decimal_is_recovered_and_counted():
    assert vs.count_broken_decimals("GDP of 2. 124 trillion and 5. 467 tons") == 2
    assert [n[1] for n in vs.extract_numbers("GDP of 2. 124 trillion")] == [2.124e12]


def test_metric_name_constants_are_not_flagged(seeded):
    _agg("eu", "poverty_headcount_pct", 4.8)
    assert _verdicts("Poverty at $3.65 per day affects 4.8% of people.")["$3.65"] == "incidental"
