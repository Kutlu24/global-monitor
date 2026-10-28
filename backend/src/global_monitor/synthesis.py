"""GLM-primary / Ollama-fallback comparison-text generation - see
config.py's own comment on why GLM is tried first (public/SEO-facing text
benefits from GLM's more reliable instruction-following over the local 7B
model). This is the project's main defense against Google's programmatic-
content penalty (see the project plan's SEO section): every bloc/compare
page gets ~100-150 genuine words synthesizing THAT page's actual current
numbers, not templated filler.

Called only when a page's underlying numbers have actually changed (see
`generate_all`'s hash-diff check) - never per-request, never for a page
whose numbers are unchanged since the last run. Every dimension/bloc/pair
in this whole site is at most 35 pages needing text, so this is a bounded,
cheap batch job, not an ongoing cost.
"""
from __future__ import annotations

import hashlib
import json
import logging

from openai import OpenAI

from . import db
from .config import settings
from .db import now
from .i18n import DEFAULT_LANG, LANGS, NATIVE_NAME, synthesis_key
from .models import SynthesisText

logger = logging.getLogger(__name__)

# Every language the site serves except English, which is what the prompts
# above write natively. A translation is generated only for a page whose
# English text was (re)generated, and is stored under its own key - so a
# page with no LLM key at all simply has no synthesis in any language,
# exactly as before.
TRANSLATE_LANGS: tuple[str, ...] = tuple(l for l in LANGS if l != DEFAULT_LANG)

_TRANSLATE_PROMPT = """You are translating one paragraph of neutral, factual data-dashboard copy \
from English into {language}. Translate the prose, and also render country names, bloc names and \
metric names in their conventional {language} forms (e.g. "Germany" -> Almanya in Turkish). Keep \
every number, unit and figure exactly as written, with the same magnitude: English "billion" is \
10^9 and "trillion" is 10^12, so use {language}'s word for exactly that size (Spanish "mil \
millones" and "billones", German "Milliarden" and "Billionen", French "milliards" and \
"billions", Chinese 十亿 and 万亿), and never drop the unit word. Keep the same length and the same factual, \
non-promotional tone. Do not add anything that is not in the source. Return only the translated \
paragraph, with no preamble, no quotation marks and no notes."""


def _data_hash(payload: dict) -> str:
    """A stable hash of whatever numbers feed a page's synthesis text -
    sorted keys so dict key ordering never causes a spurious "changed"
    result to trigger an unnecessary (and costly) regeneration."""
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


# Confirmed live (2026-09-27): glm-4.5-flash is a reasoning model - it
# spends completion tokens on an internal `reasoning_content` field BEFORE
# emitting the real, visible `content`, and a 300-token budget (plenty for
# a plain non-reasoning model's ~150-word answer) was consumed entirely by
# reasoning on some calls, leaving `content` empty. Every synthesis row
# silently failed to save (an empty string fails the `if not text: return`
# guard in _maybe_generate) with no exception and no error logged - this
# is why 1200, not 300: real headroom for the reasoning trace AND the
# actual ~150-word answer, confirmed by direct API inspection (a
# one-sentence test prompt alone used 178 completion tokens, nearly all of
# it reasoning_content).
GENERATION_MAX_TOKENS = 1200


def _call_glm(prompt: str, think: bool = True) -> str:
    client = OpenAI(api_key=settings.glm_api_key, base_url=settings.glm_base_url)
    # A translation needs no reasoning trace; measured 2026-10-28 on a zh page: with thinking on,
    # 2 of 4 calls used all 1200 tokens on reasoning and returned empty content, with it off
    # 4 of 4 finished in about 250 tokens.
    extra = {} if think else {"extra_body": {"thinking": {"type": "disabled"}}}
    resp = client.chat.completions.create(
        model=settings.glm_model, messages=[{"role": "user", "content": prompt}],
        max_tokens=GENERATION_MAX_TOKENS, **extra,
    )
    return (resp.choices[0].message.content or "").strip()


def _call_ollama(prompt: str) -> str:
    client = OpenAI(api_key="ollama", base_url=f"{settings.ollama_base_url}/v1")
    resp = client.chat.completions.create(
        model=settings.ollama_model, messages=[{"role": "user", "content": prompt}],
        max_tokens=GENERATION_MAX_TOKENS,
    )
    return (resp.choices[0].message.content or "").strip()


def _generate_text(prompt: str, think: bool = True) -> tuple[str, str, str]:
    """Returns (text, provider, model). GLM first if a key is configured;
    any failure (network, quota, bad key) OR an empty response (confirmed
    real failure mode - see GENERATION_MAX_TOKENS's own comment: a
    reasoning model can still come back empty in edge cases even with a
    generous budget) falls back to the local Ollama model rather than
    leaving the page with no synthesis text at all."""
    if settings.synthesis_provider == "glm" and settings.glm_api_key:
        try:
            text = _call_glm(prompt, think)
            if text:
                return text, "glm", settings.glm_model
            logger.warning("GLM synthesis call returned empty content, falling back to Ollama")
        except Exception:
            logger.exception("GLM synthesis call failed, falling back to Ollama")
    return _call_ollama(prompt), "ollama", settings.ollama_model


# A paragraph whose numbers are not in the prompt's data is sent back this many
# times with the offending numbers listed. A small local model fails the audit
# on ~80% of pages, GLM on ~20% (see docs/synthesis-verification.md).
VERIFY_RETRIES = 2


_SENTENCE_END = (".", "!", "?", ")", '"', "\u201d", "\u00bb", "\u3002", "\uff01", "\uff1f")


def _is_complete(text: str) -> bool:
    """False for text that stops mid-sentence. A reasoning model that spends its token
    budget thinking returns whatever fit, with no error (see GENERATION_MAX_TOKENS)."""
    return text.rstrip().endswith(_SENTENCE_END)


# A paragraph with no figures has nothing to be wrong about, so the number audit passes it. The
# local fallback model does this: 4 of 18 pages it wrote on 2026-10-28 stated 0 to 3 figures.
MIN_FIGURES = 4


def _figure_count(text: str) -> int:
    from . import verify_synthesis as vs

    return sum(1 for surface, _v, _step, _klass, marker in vs.extract_numbers(text) if marker or "." in surface)


def _verified_text(page_key: str, prompt: str, text: str, provider: str, model: str):
    """Audit `text` against the figures behind `page_key` (bloc:/compare: pages
    only for the numbers; every page for completeness) and ask for a rewrite while
    it has numbers that are not in the data or stops mid-sentence. Returns
    (text, provider, model, ok); ok is False if the last draft still fails, in
    which case the caller must not publish it."""
    from . import verify_synthesis as vs  # imports this module, so not at top level

    for attempt in range(VERIFY_RETRIES + 1):
        row = SynthesisText(page_key=page_key, text=text, data_hash="", generated_at="", provider=provider, model=model)
        report = vs.verify_page(row)
        numbers_ok = report is None or report.clean
        complete = _is_complete(text)
        enough = report is None or _figure_count(text) >= MIN_FIGURES
        if numbers_ok and complete and enough:
            return text, provider, model, True
        if attempt == VERIFY_RETRIES:
            break
        logger.warning("Synthesis for %s is %s, asking for a rewrite (%d/%d)", page_key,
                       "cut off" if not complete else ("unverified" if not numbers_ok else "too vague"),
                       attempt + 1, VERIFY_RETRIES)
        if numbers_ok and complete and not enough:
            retry = (f"{prompt}\n\nYour previous draft states only {_figure_count(text)} figures:\n{text}\n\n"
                     f"Write the paragraph again and state at least {MIN_FIGURES} of the real figures listed above, "
                     "each with its unit.")
        elif not complete:
            retry = (f"{prompt}\n\nYour previous draft stopped mid-sentence:\n{text}\n\n"
                     "Write the complete paragraph again, a little shorter, ending with a full stop.")
        else:
            retry = vs.feedback_prompt(prompt, text, report)
        try:
            text, provider, model = _generate_text(retry)
        except Exception:
            logger.exception("Synthesis rewrite failed for %s", page_key)
            break
        if not text:
            break
    return text, provider, model, False


def _translation_problems(page_key: str, lang: str, english_text: str, text: str, data_hash: str) -> list[str]:
    """What is wrong with a translation, as sentences a model can act on; empty means accept.
    Dropped figures are not a reason to reject: that finding is too noisy (see
    verify_translations.py)."""
    from . import verify_translations as vt

    row = SynthesisText(page_key=synthesis_key(page_key, lang), text=text, data_hash=data_hash,
                        generated_at="", provider="", model="")
    english = SynthesisText(page_key=page_key, text=english_text, data_hash=data_hash,
                            generated_at="", provider="", model="")
    r = vt.audit_translation(row, english)
    problems = []
    if r.same_as_en:
        problems.append("it is identical to the English text")
    if r.wrong_script:
        problems.append(f"it is not written in {NATIVE_NAME[lang]}")
    if r.truncated:
        problems.append("it stops mid-sentence")
    if r.scale_diff:
        problems.append(f"these figures have the wrong magnitude or lost their unit word: {', '.join(r.scale_diff)} "
                        "(English billion = 10^9, trillion = 10^12)")
    if r.changed:
        problems.append(f"these figures are not in the English text: {', '.join(r.changed)}")
    return problems


def _translate(page_key: str, lang: str, english_text: str, data_hash: str) -> bool:
    """Translate one page into one language, audit it against the English text, send it back
    while it has problems, and store it only if it passes. False leaves the prior text."""
    base = _TRANSLATE_PROMPT.format(language=NATIVE_NAME[lang]) + "\n\n" + english_text
    try:
        text, provider, model = _generate_text(base, think=False)
    except Exception:
        logger.exception("Synthesis translation failed for %s [%s] - keeping prior text", page_key, lang)
        return False
    for attempt in range(VERIFY_RETRIES + 1):
        if not text:
            return False
        problems = _translation_problems(page_key, lang, english_text, text, data_hash)
        if not problems:
            break
        if attempt == VERIFY_RETRIES:
            logger.warning("Translation of %s [%s] still has problems after %d rewrites (%s) - keeping prior text",
                           page_key, lang, VERIFY_RETRIES, "; ".join(problems))
            return False
        try:
            text, provider, model = _generate_text(
                think=False, prompt=f"{base}\n\nYour previous translation was:\n{text}\n\nIt was rejected because "
                f"{'; '.join(problems)}. Translate the English text again and fix this.")
        except Exception:
            logger.exception("Translation rewrite failed for %s [%s]", page_key, lang)
            return False
    db.upsert_synthesis(SynthesisText(
        page_key=synthesis_key(page_key, lang), text=text, data_hash=data_hash, generated_at=now(),
        provider=provider, model=model,
    ))
    return True


def _maybe_generate(page_key: str, payload_for_hash: dict, prompt: str) -> None:
    """The actual hash-diff gate: skip the (real, costly) LLM call entirely
    if this page's underlying numbers haven't changed since the last run."""
    new_hash = _data_hash(payload_for_hash)
    existing = db.get_synthesis(page_key)
    if existing is not None and existing.data_hash == new_hash:
        return
    try:
        text, provider, model = _generate_text(prompt)
    except Exception:
        logger.exception("Synthesis generation failed entirely for %s - leaving prior text in place", page_key)
        return
    if not text:
        return
    text, provider, model, ok = _verified_text(page_key, prompt, text, provider, model)
    if not ok or not text:
        logger.warning("Synthesis for %s still has unverified numbers after %d rewrites - keeping prior text",
                       page_key, VERIFY_RETRIES)
        return
    db.upsert_synthesis(SynthesisText(
        page_key=page_key, text=text, data_hash=new_hash, generated_at=now(), provider=provider, model=model,
    ))
    _maybe_translate(page_key, text, new_hash)


def _translate_or_drop(page_key: str, lang: str, english_text: str, data_hash: str) -> bool:
    """_translate, and if it fails while the stored translation belongs to older English
    figures, delete that row: _synthesis_payload then serves the English text, which is
    right, instead of a translation of numbers that no longer match."""
    if _translate(page_key, lang, english_text, data_hash):
        return True
    key = synthesis_key(page_key, lang)
    old = db.get_synthesis(key)
    if old is not None and old.data_hash != data_hash:
        logger.warning("Dropping stale translation %s: it no longer matches the English text", key)
        db.delete_synthesis(key)
    return False


def _maybe_translate(page_key: str, english_text: str, data_hash: str) -> None:
    """Translate a page's freshly generated English text into the other seven
    languages, each gated on the same data hash. A failed translation leaves
    that language's previous text (or the English fallback the API serves)
    in place - one missing language never blocks the other six."""
    for lang in TRANSLATE_LANGS:
        existing = db.get_synthesis(synthesis_key(page_key, lang))
        if existing is not None and existing.data_hash == data_hash:
            continue
        _translate_or_drop(page_key, lang, english_text, data_hash)


def generate_translations() -> int:
    """Backfill pass: every English synthesis row that exists but has no
    translation (or one whose English text changed since) gets one. Called
    from the daily pipeline so a language added later, or a failed run, is
    repaired on the next cycle without a manual step. Returns the number of
    rows translated."""
    done = 0
    for row in db.list_synthesis():
        if "|" in row.page_key:
            continue  # already a translation
        for lang in TRANSLATE_LANGS:
            existing = db.get_synthesis(synthesis_key(row.page_key, lang))
            if existing is not None and existing.data_hash == row.data_hash:
                continue
            done += _translate_or_drop(row.page_key, lang, row.text, row.data_hash)
    return done


def _bloc_snapshot(bloc_id: str) -> dict:
    return {m.metric_id: (a.value, a.period) for m in db.get_metrics()
            if (a := db.latest_bloc_aggregate(bloc_id, m.metric_id)) is not None}


def _bloc_prompt(bloc) -> str:
    metric_lines = []
    for m in db.get_metrics():
        agg = db.latest_bloc_aggregate(bloc.bloc_id, m.metric_id)
        if agg is not None and agg.value is not None:
            metric_lines.append(f"- {m.name}: {agg.value:.4g} {m.unit} ({agg.period})")
    return (
        f"You are writing one short paragraph (100-150 words) for a public data dashboard page "
        f"about {bloc.name} ({bloc.description}). Using ONLY the real figures below, write a "
        f"factual, neutral summary of {bloc.name}'s current economic, trade, social, and military "
        f"position. Do not invent any numbers not listed here. Do not use markdown formatting.\n\n"
        f"Real data:\n" + "\n".join(metric_lines)
    )


def _compare_prompt(a, b, dimension: str | None = None) -> str:
    scope = f"their {dimension} data" if dimension else "their economic, trade, social, and military data"
    lines = []
    metrics = db.get_metrics() if dimension is None else [m for m in db.get_metrics() if m.dimension == dimension]
    for m in metrics:
        agg_a = db.latest_bloc_aggregate(a.bloc_id, m.metric_id)
        agg_b = db.latest_bloc_aggregate(b.bloc_id, m.metric_id)
        va = f"{agg_a.value:.4g}" if agg_a and agg_a.value is not None else "N/A"
        vb = f"{agg_b.value:.4g}" if agg_b and agg_b.value is not None else "N/A"
        lines.append(f"- {m.name} ({m.unit}): {a.name}={va}, {b.name}={vb}")
    return (
        f"You are writing one short paragraph (100-150 words) comparing {a.name} and {b.name} on "
        f"a public data dashboard, focused on {scope}. Using ONLY the real figures below, write a "
        f"factual, neutral comparison - name which side leads on which metric and by roughly how "
        f"much. Do not invent any numbers not listed here. Do not use markdown formatting.\n\n"
        f"Real data:\n" + "\n".join(lines)
    )


# The 6 pairwise combinations of the 4 blocs that participate in the main
# compare structure - brics5 deliberately excluded, same as
# frontend/src/lib/pairs.ts (it's a secondary historical view of `brics`,
# not a 5th comparison target). Kept here rather than shared with the
# frontend module since the two run in different languages/processes;
# duplicating four bloc ids is far simpler than a cross-language shared
# constant for something this small and this unlikely to change.
_COMPARE_BLOCS = ["brics", "eu", "us", "usmca"]
_COMPARE_PAIRS = [(_COMPARE_BLOCS[i], _COMPARE_BLOCS[j])
                   for i in range(len(_COMPARE_BLOCS)) for j in range(i + 1, len(_COMPARE_BLOCS))]
_DIMENSIONS = ["economic", "trade", "social", "military"]


# --- Tension module (GDELT-derived, hours-scale) - see tension.py's own
# docstring for where this data comes from. A stricter, GFCA-inherited
# system prompt than the bloc/compare prompts above: this is live
# geopolitical event data, not a slow structural indicator, so the
# anti-fabrication rules are spelled out explicitly rather than relying on
# "use only the real figures below" alone. ---

_TENSION_SYSTEM_PROMPT = """You are a research assistant summarizing real, recent geopolitical \
event data for a public data-dashboard reader. You will be given aggregate statistics and \
specific example events, all computed directly from the GDELT 2.0 Event Database (a real, \
automated global event-coding system - not a curated or verified source).

Rules:
- You are writing an INTERPRETATION of the data given, not a prediction or forecast. Never state \
a probability of war, conflict, or any other outcome. Never invent a "confidence score."
- Every specific claim must trace to a number or example event in the data provided. Do not add \
outside knowledge, historical context, or claims about intentions/motives the data doesn't support.
- Name the real limitations of this data plainly: GDELT is fully automated (event coding errors \
are common), it over-represents English-language and Western media, the observation window is \
short (hours), and event counts/tone reflect media coverage volume, not ground truth.
- If the data is thin (few events, no examples), say so rather than filling the gap with speculation.
- End with a short, explicit sentence that this is not a verified forecast and should not be the \
sole basis for any decision.
- 80-120 words. No markdown formatting.
"""


def _format_tension_example(ex: dict) -> str:
    parts = [f"[{ex['date']}]"]
    if ex.get("actor1") or ex.get("actor2"):
        parts.append(f"{ex.get('actor1') or '?'} -> {ex.get('actor2') or '?'}")
    if ex.get("location"):
        parts.append(f"at {ex['location']}")
    if ex.get("goldstein") is not None:
        parts.append(f"Goldstein={ex['goldstein']:.1f}")
    if ex.get("source_url"):
        parts.append(f"source: {ex['source_url']}")
    return " ".join(parts)


def _tension_prompt(label: str, score) -> str:
    lines = [
        f"Subject: {label}",
        f"Window: last {score.window_hours:.0f} hours",
        f"Total matching events: {score.n_events}",
        f"Mean Goldstein score (-10 conflictual .. +10 cooperative): "
        f"{score.mean_goldstein:.2f}" if score.mean_goldstein is not None else "Mean Goldstein score: n/a",
        f"Mean article tone (-100..+100, 0=neutral): "
        f"{score.mean_tone:.2f}" if score.mean_tone is not None else "Mean article tone: n/a",
        f"Event type breakdown: {score.verbal_cooperation} verbal-cooperation, "
        f"{score.material_cooperation} material-cooperation, {score.verbal_conflict} verbal-conflict, "
        f"{score.material_conflict} material-conflict"
        + (f" (conflict share: {score.conflict_share:.0%})" if score.conflict_share is not None else ""),
        f"Trend within window (second half mean Goldstein - first half): "
        f"{score.goldstein_delta:+.2f}" if score.goldstein_delta is not None else "Trend: not enough dated events to compute",
        "",
        "Most conflictual real events in this window:",
    ]
    conflictual = [e for e in score.examples if e["kind"] == "conflictual"]
    cooperative = [e for e in score.examples if e["kind"] == "cooperative"]
    lines += [f"  - {_format_tension_example(e)}" for e in conflictual] or ["  (none)"]
    lines += ["", "Most cooperative real events in this window:"]
    lines += [f"  - {_format_tension_example(e)}" for e in cooperative] or ["  (none)"]
    return f"{_TENSION_SYSTEM_PROMPT}\n\nData:\n\n" + "\n".join(lines) + "\n\nWrite the situational summary."


def generate_tension_synthesis(bloc_by_id: dict) -> None:
    """Separate from generate_all() - called from tension.py's own,
    hours-scale refresh cycle (scheduler.py), never from the daily/weekly
    ETL. page_key uses a `tension:` prefix so it never collides with the
    structural bloc:/compare: keys above."""
    for score in db.get_all_tension_scores():
        if score.scope.startswith("bloc:"):
            bloc_id = score.scope.removeprefix("bloc:")
            bloc = bloc_by_id.get(bloc_id)
            label = bloc.name if bloc else bloc_id
        else:
            a_id, b_id = score.scope.removeprefix("pair:").split("-", 1)
            a, b = bloc_by_id.get(a_id), bloc_by_id.get(b_id)
            label = f"{a.name if a else a_id} vs {b.name if b else b_id}"
        # Deliberately excludes computed_at - that changes every refresh
        # cycle regardless of whether the real numbers moved, which would
        # defeat the whole point of the hash-diff gate (an LLM call every
        # 2 hours even when nothing actually changed).
        payload = {
            "n_events": score.n_events, "mean_goldstein": score.mean_goldstein,
            "mean_tone": score.mean_tone, "conflict_share": score.conflict_share,
            "goldstein_delta": score.goldstein_delta, "examples": score.examples,
        }
        _maybe_generate(f"tension:{score.scope}", payload, _tension_prompt(label, score))


def generate_all() -> None:
    blocs = db.get_blocs()
    for bloc in blocs:
        payload = _bloc_snapshot(bloc.bloc_id)
        if not payload:
            continue
        _maybe_generate(f"bloc:{bloc.bloc_id}", payload, _bloc_prompt(bloc))

    bloc_by_id = {b.bloc_id: b for b in blocs}
    for a_id, b_id in _COMPARE_PAIRS:
        a, b = bloc_by_id.get(a_id), bloc_by_id.get(b_id)
        if a is None or b is None:
            continue
        overview_payload = {**{f"a:{k}": v for k, v in _bloc_snapshot(a_id).items()},
                             **{f"b:{k}": v for k, v in _bloc_snapshot(b_id).items()}}
        if overview_payload:
            _maybe_generate(f"compare:{a_id}-vs-{b_id}", overview_payload, _compare_prompt(a, b))
        for dimension in _DIMENSIONS:
            dim_metrics = [m.metric_id for m in db.get_metrics() if m.dimension == dimension]
            dim_payload = {
                **{f"a:{k}": v for k, v in _bloc_snapshot(a_id).items() if k in dim_metrics},
                **{f"b:{k}": v for k, v in _bloc_snapshot(b_id).items() if k in dim_metrics},
            }
            if dim_payload:
                _maybe_generate(f"compare:{a_id}-vs-{b_id}:{dimension}", dim_payload, _compare_prompt(a, b, dimension))
