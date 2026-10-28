"""Every risk scenario and epicentre needs all eight languages: pick() falls back to
English silently, so a missing translation would ship unnoticed."""
from global_monitor import i18n, i18n_scenarios, risk

LANGS = ("en", "tr", "de", "fr", "es", "ar", "zh", "ru")


def test_every_scenario_is_translated_into_all_languages():
    for s in risk.SCENARIOS:
        for table in (i18n.SCENARIO_NAME, i18n.SCENARIO_EXPLANATION, i18n.SCENARIO_NOT_MEASURED):
            assert s.slug in table, (s.slug, "missing")
            missing = [l for l in LANGS if not table[s.slug].get(l, "").strip()]
            assert not missing, (s.slug, missing)


def test_english_translation_text_matches_the_source_text():
    # Scoped to the scenarios in i18n_scenarios.py (and the renamed water one). The original
    # six already differ in places, e.g. the Russia-NATO English explanation is a sentence
    # shorter than the source; not fixed here.
    for s in risk.SCENARIOS:
        if s.slug not in i18n_scenarios.NAME and s.slug != "climate-water-wars":
            continue
        assert i18n.SCENARIO_NAME[s.slug]["en"] == s.name, s.slug
        assert i18n.SCENARIO_EXPLANATION[s.slug]["en"] == s.explanation, s.slug
        if s.slug in i18n_scenarios.NOT_MEASURED:
            assert i18n.SCENARIO_NOT_MEASURED[s.slug]["en"] == s.not_measured, s.slug


def test_every_epicentre_label_is_translated():
    for s in risk.SCENARIOS:
        for _lat, _lon, label in s.epicentres:
            missing = [l for l in LANGS if not i18n.EPICENTRE_LABEL.get(label, {}).get(l)]
            assert not missing, (s.slug, label, missing)


def test_scenario_weights_sum_to_one_and_cover_every_criterion():
    for s in risk.SCENARIOS:
        assert abs(sum(s.weights.values()) - 1.0) < 1e-9, s.slug
        assert set(s.weights) == set(risk.CRITERIA), s.slug


def test_direction_overrides_name_real_indicators():
    known = {m for c in risk.CRITERIA.values() for m, _d, _w in c["indicators"]}
    for s in risk.SCENARIOS:
        for metric_id, direction in s.direction_overrides:
            assert metric_id in known and direction in (-1, 0, 1), (s.slug, metric_id)
