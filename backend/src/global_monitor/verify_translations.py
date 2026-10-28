"""Audit of the translated bloc/compare paragraphs against their English source.

verify_synthesis.py checks the English paragraph against the data. A translation
is generated from that English text, so the question for it is different: did it
keep every figure? For each stored `page_key|lang` row this compares the numbers
written in the translation with the numbers in the English row of the same page.

  match         the translation's number equals an English number (scale words in
                the target language are read: trilyon, Milliarden, 万亿, трлн ...)
  scale_diff    same significant digits, different power of ten - a false friend
                (German "Billion" is 10^12, English "billion" is 10^9) or a slip
  changed       no English number has these digits: a figure was altered or invented
  dropped       an English number that the translation does not contain
  wrong_script  the text is not in the language's script (Arabic, Chinese, Russian)
  same_as_en    the translation is the English text unchanged
  truncated     the text does not end in a sentence terminator
  stale         the translation's data hash differs from its English row

Read-only: no database write, no LLM call.
"""
from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, field

from . import db
from .verify_synthesis import extract_numbers

# Words that scale the number before them, per language. Longest first so
# "mil millones" is not read as "mil".
_SCALE_WORDS: dict[str, list[tuple[str, float]]] = {
    "tr": [("trilyon", 1e12), ("milyar", 1e9), ("milyon", 1e6), ("bin", 1e3)],
    "de": [("billionen", 1e12), ("billion", 1e12), ("bio.", 1e12), ("milliarden", 1e9), ("milliarde", 1e9),
           ("mrd", 1e9), ("millionen", 1e6), ("million", 1e6), ("mio", 1e6), ("tausend", 1e3)],
    "fr": [("billions", 1e12), ("billion", 1e12), ("milliards", 1e9), ("milliard", 1e9), ("md", 1e9),
           ("millions", 1e6), ("million", 1e6), ("mille", 1e3)],
    "es": [("billones", 1e12), ("billón", 1e12), ("miles de millones", 1e9), ("mil millones", 1e9), ("millones", 1e6),
           ("millón", 1e6), ("mil", 1e3)],
    "ar": [("تريليون", 1e12), ("مليار", 1e9), ("مليون", 1e6), ("ألف", 1e3)],
    "zh": [("万亿", 1e12), ("亿", 1e8), ("万", 1e4), ("千", 1e3)],
    "ru": [("трлн", 1e12), ("триллион", 1e12), ("млрд", 1e9), ("миллиард", 1e9),
           ("млн", 1e6), ("миллион", 1e6), ("тысяч", 1e3), ("тыс", 1e3)],
}
# A language is "in script" when this share of its letters belongs to the script.
_SCRIPT = {"ar": "ARABIC", "zh": "CJK", "ru": "CYRILLIC"}
_SCRIPT_MIN = 0.5
_REL = 1e-6

_TOKEN = re.compile(
    r"(?<![\d.])(?:\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?!\d)(?:[.,]\d+)?"  # "54 400", "1 234,5"
    r"|\d[\d.,\u066b\u066c]*\d(?:[eE][+-]?\d+)?|\d(?:[eE][+-]?\d+)?)")


def _ascii_digits(text: str) -> str:
    return "".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in text)


def _mantissas(token: str) -> list[float]:
    """All readings of a written number. "1,234" is 1234 or 1.234; "2,5" is 2.5; "1.234,5" is 1234.5."""
    t = token.replace("٫", ".").replace("٬", ",").strip()
    t = re.sub(r"[ \u00a0\u202f]", "", t)  # "54 400": space-separated thousands
    if re.fullmatch(r"\d+(?:\.\d+)?[eE][+-]?\d+", t):  # 3.102e+13, copied from the prompt
        return [float(t)]

    seps = re.findall(r"[.,]", t)
    parts = re.split(r"[.,]", t)
    try:
        if not seps:
            return [float(t)]
        if len(set(seps)) == 2:
            return [float("".join(parts[:-1]) + "." + parts[-1])]
        if len(seps) > 1:
            return [float("".join(parts))]
        out = [float(parts[0] + "." + parts[1])]
        if len(parts[1]) == 3:
            out.append(float("".join(parts)))
        return out
    except ValueError:
        return []


def _digits(value: float) -> str:
    """Significant digits of a value with its power of ten removed, to spot scale slips."""
    if value == 0:
        return "0"
    mant = value / 10 ** math.floor(math.log10(abs(value)))
    return f"{mant:.4f}".rstrip("0").rstrip(".")


def translation_numbers(text: str, lang: str) -> list[tuple[str, list[float]]]:
    """(surface, candidate absolute values) for every number in a translated text."""
    text = _ascii_digits(text)
    out = []
    for m in _TOKEN.finditer(text):
        mants = _mantissas(m.group(0))
        if not mants:
            continue
        tail = text[m.end():m.end() + 14].lower().lstrip()
        scale = 1.0
        for word, mult in _SCALE_WORDS.get(lang, []):
            if tail.startswith(word):
                scale = mult
                break
        out.append((m.group(0).strip(), [v * scale for v in mants]))
    return out


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= _REL * max(abs(a), abs(b), 1e-12)


@dataclass
class TranslationReport:
    page_key: str
    lang: str
    provider: str
    model: str
    stale: bool = False
    same_as_en: bool = False
    wrong_script: bool = False
    truncated: bool = False
    matched: int = 0
    scale_diff: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not (self.same_as_en or self.wrong_script or self.truncated or self.scale_diff
                    or self.changed or self.dropped)


def _in_script(text: str, lang: str) -> bool:
    want = _SCRIPT.get(lang)
    if not want:
        return True
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    return sum(want in unicodedata.name(c, "") for c in letters) / len(letters) >= _SCRIPT_MIN


def audit_translation(row, english) -> TranslationReport:
    lang = row.page_key.split("|", 1)[1]
    r = TranslationReport(row.page_key, lang, row.provider, row.model,
                          stale=row.data_hash != english.data_hash)
    r.same_as_en = row.text.strip() == english.text.strip()
    r.wrong_script = not _in_script(row.text, lang)
    r.truncated = not row.text.rstrip().endswith((".", "!", "?", "。", "！", "？", "»", "”", ")", "\""))

    en_values = [v for _s, v, _step, _k, _m in extract_numbers(english.text)]
    en_digits = {_digits(v) for v in en_values}
    seen: list[float] = []
    for surface, cands in translation_numbers(row.text, lang):
        hit = next((v for v in en_values for c in cands if _close(v, c)), None)
        if hit is not None:
            r.matched += 1
            seen.append(hit)
        elif any(_digits(c) in en_digits for c in cands):
            r.scale_diff.append(surface)
        else:
            r.changed.append(surface)
    # Only report a dropped figure when the translation is otherwise in the right language.
    if not r.wrong_script and not r.same_as_en:
        r.dropped = sorted({f"{v:g}" for v in en_values if not any(_close(v, s) for s in seen)})
    return r


def verify_all() -> list[TranslationReport]:
    rows = {r.page_key: r for r in db.list_synthesis()}
    out = []
    for key, row in sorted(rows.items()):
        if "|" not in key:
            continue
        english = rows.get(key.split("|", 1)[0])
        if english is not None:
            out.append(audit_translation(row, english))
    return out


def summarize(reports: list[TranslationReport]) -> dict:
    def n(pred):
        return sum(1 for r in reports if pred(r))

    by_provider = {}
    for r in reports:
        p = by_provider.setdefault(f"{r.provider}:{r.model}", {"rows": 0, "clean": 0})
        p["rows"] += 1
        p["clean"] += r.clean
    return {
        "rows": len(reports), "clean": n(lambda r: r.clean), "stale": n(lambda r: r.stale),
        "same_as_en": n(lambda r: r.same_as_en), "wrong_script": n(lambda r: r.wrong_script),
        "truncated": n(lambda r: r.truncated), "with_scale_diff": n(lambda r: r.scale_diff),
        "with_changed": n(lambda r: r.changed), "with_dropped": n(lambda r: r.dropped),
        "by_provider": by_provider,
    }
