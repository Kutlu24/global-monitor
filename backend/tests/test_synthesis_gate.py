"""The generation gate beyond numbers: complete sentences, and audited translations."""
from global_monitor import db, synthesis
from global_monitor.models import BlocAggregate

EN = "The EU has a GDP of $21.24 trillion and spends 2.18% of GDP on defence."


import pytest


@pytest.fixture(autouse=True)
def _one_figure_is_enough(monkeypatch):
    """The sample paragraphs here state two figures; the figure-count rule has its own test."""
    monkeypatch.setattr(synthesis, "MIN_FIGURES", 1)


def _agg(metric_id, value):
    db.upsert_bloc_aggregate(BlocAggregate("eu", metric_id, "2025", value, 3, "2026-01-01T00:00:00+00:00"))


def _drafts(monkeypatch, drafts):
    it, prompts = iter(drafts), []

    def fake(prompt, think=True):
        prompts.append(prompt)
        return next(it), "t", "t"

    monkeypatch.setattr(synthesis, "_generate_text", fake)
    return prompts


def test_a_cut_off_paragraph_is_rewritten(seeded, monkeypatch):
    _agg("gdp_current_usd", 21.243e12)
    _agg("military_exp_pct_gdp", 2.1794)
    prompts = _drafts(monkeypatch, ["The EU has a GDP of $21.24 trillion and spends 2.18% of GDP on defence."])
    text, _, _, ok = synthesis._verified_text("bloc:eu", "P", "The EU has a GDP of $21.24 trillion and", "t", "t")
    assert ok and text.endswith(".") and "stopped mid-sentence" in prompts[0]


def test_a_paragraph_that_stays_cut_off_is_refused(seeded, monkeypatch):
    _agg("gdp_current_usd", 21.243e12)
    _drafts(monkeypatch, ["The EU has a GDP of", "The EU has"])
    *_, ok = synthesis._verified_text("bloc:eu", "P", "The EU has a GDP of $21.24 trillion and", "t", "t")
    assert ok is False


def test_translation_with_a_wrong_magnitude_is_sent_back(seeded, monkeypatch):
    bad = "La UE tiene un PIB de 21,24 mil millones $ y gasta 2,18 % en defensa."  # 10^9, not 10^12
    good = "La UE tiene un PIB de 21,24 billones $ y gasta 2,18 % en defensa."
    prompts = _drafts(monkeypatch, [bad, good])
    assert synthesis._translate("bloc:eu", "es", EN, "h1")
    assert db.get_synthesis("bloc:eu|es").text == good
    assert "wrong magnitude" in prompts[1]


def test_translation_that_keeps_failing_is_not_stored(seeded, monkeypatch):
    bad = "La UE tiene un PIB de 21,24 mil millones $ y gasta 2,18 % en defensa."
    _drafts(monkeypatch, [bad, bad, bad])
    assert synthesis._translate("bloc:eu", "es", EN, "h1") is False
    assert db.get_synthesis("bloc:eu|es") is None


def test_a_failed_translation_drops_the_stale_one(seeded, monkeypatch):
    from global_monitor.models import SynthesisText
    bad = "La UE tiene un PIB de 21,24 mil millones $ y gasta 2,18 % en defensa."
    db.upsert_synthesis(SynthesisText(page_key="bloc:eu|es", text="viejo", data_hash="h0",
                                      generated_at="2026-01-01T00:00:00+00:00", provider="t", model="t"))
    _drafts(monkeypatch, [bad, bad, bad])
    assert synthesis._translate_or_drop("bloc:eu", "es", EN, "h1") is False
    assert db.get_synthesis("bloc:eu|es") is None


def test_a_failed_translation_keeps_a_current_one(seeded, monkeypatch):
    from global_monitor.models import SynthesisText
    bad = "La UE tiene un PIB de 21,24 mil millones $ y gasta 2,18 % en defensa."
    db.upsert_synthesis(SynthesisText(page_key="bloc:eu|es", text="actual", data_hash="h1",
                                      generated_at="2026-01-01T00:00:00+00:00", provider="t", model="t"))
    _drafts(monkeypatch, [bad, bad, bad])
    assert synthesis._translate_or_drop("bloc:eu", "es", EN, "h1") is False
    assert db.get_synthesis("bloc:eu|es").text == "actual"


def test_a_paragraph_with_too_few_figures_is_sent_back(seeded, monkeypatch):
    for metric_id, value in (("gdp_current_usd", 21.243e12), ("military_exp_pct_gdp", 2.1794),
                             ("trade_pct_gdp", 40.1), ("life_expectancy_years", 80.9)):
        _agg(metric_id, value)
    monkeypatch.setattr(synthesis, "MIN_FIGURES", 4)
    vague = "The EU is a large economy with strong trade and a long-lived population."
    good = ("The EU has a GDP of $21.24 trillion, spends 2.18% of GDP on defence, trades 40.1% of GDP "
            "and has a life expectancy of 80.9 years.")
    prompts = _drafts(monkeypatch, [good])
    text, _, _, ok = synthesis._verified_text("bloc:eu", "P", vague, "t", "t")
    assert ok and text == good and "states only 0 figures" in prompts[0]
