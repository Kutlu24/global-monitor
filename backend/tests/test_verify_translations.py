"""verify_translations.py: figures kept across languages. No LLM, no network."""
from global_monitor import verify_translations as vt
from global_monitor.models import SynthesisText


def _row(key, text, h="h"):
    return SynthesisText(page_key=key, text=text, data_hash=h, generated_at="", provider="t", model="t")


EN = _row("bloc:eu", "The EU has a GDP of $21.24 trillion, spends 2.18% of GDP on defence and has 1,000 sites.")


def _audit(text, lang="de"):
    return vt.audit_translation(_row(f"bloc:eu|{lang}", text), EN)


def test_faithful_translation_is_clean_even_with_decimal_commas():
    r = _audit("Die EU hat ein BIP von 21,24 Billionen $, gibt 2,18 % des BIP für Verteidigung aus und hat 1.000 Standorte.")
    assert r.clean, (r.scale_diff, r.changed, r.dropped)


def test_changed_figure_is_flagged():
    r = _audit("Die EU hat ein BIP von 21,24 Billionen $, gibt 3,18 % des BIP aus und hat 1.000 Standorte.")
    assert "3,18" in r.changed and "2.18" in r.dropped


def test_german_billion_is_not_english_billion():
    # English "billion" is 10^9; German "Billion" is 10^12 - a model that keeps the word but
    # not the meaning changes the figure by a thousand.
    en = _row("bloc:eu", "Military spending is $460 billion.")
    r = vt.audit_translation(_row("bloc:eu|de", "Die Militärausgaben betragen 460 Billionen $."), en)
    assert r.scale_diff == ["460"]


def test_chinese_scale_words_are_read():
    en = _row("bloc:eu", "GDP is $21.24 trillion.")
    assert vt.audit_translation(_row("bloc:eu|zh", "国内生产总值为21.24万亿美元。"), en).clean


def test_arabic_indic_digits_and_script():
    en = _row("bloc:eu", "Growth is 2.5%.")
    assert vt.audit_translation(_row("bloc:eu|ar", "النمو ٢٫٥٪."), en).matched == 1
    assert vt.audit_translation(_row("bloc:eu|ar", "Growth is 2.5%."), en).same_as_en


def test_wrong_script_and_truncation():
    en = _row("bloc:eu", "Growth is 2.5%.")
    assert vt.audit_translation(_row("bloc:eu|ru", "Growth is 2.5% in the euro area."), en).wrong_script
    assert vt.audit_translation(_row("bloc:eu|de", "Das Wachstum liegt bei 2,5 %,"), en).truncated


def test_years_next_to_each_other_stay_separate_numbers():
    nums = vt.translation_numbers("zwischen 2023 2024 und 2025", "de")
    assert [s for s, _ in nums] == ["2023", "2024", "2025"]


def test_scientific_notation_and_space_thousands_are_single_numbers():
    nums = dict(vt.translation_numbers("BIP 3.102e+13 und 54 400 Einwohner", "de"))
    assert nums["3.102e+13"] == [3.102e13] and nums["54 400"] == [54400.0]
