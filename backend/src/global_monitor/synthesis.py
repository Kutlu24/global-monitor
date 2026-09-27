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
from .models import SynthesisText

logger = logging.getLogger(__name__)


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


def _call_glm(prompt: str) -> str:
    client = OpenAI(api_key=settings.glm_api_key, base_url=settings.glm_base_url)
    resp = client.chat.completions.create(
        model=settings.glm_model, messages=[{"role": "user", "content": prompt}],
        max_tokens=GENERATION_MAX_TOKENS,
    )
    return (resp.choices[0].message.content or "").strip()


def _call_ollama(prompt: str) -> str:
    client = OpenAI(api_key="ollama", base_url=f"{settings.ollama_base_url}/v1")
    resp = client.chat.completions.create(
        model=settings.ollama_model, messages=[{"role": "user", "content": prompt}],
        max_tokens=GENERATION_MAX_TOKENS,
    )
    return (resp.choices[0].message.content or "").strip()


def _generate_text(prompt: str) -> tuple[str, str, str]:
    """Returns (text, provider, model). GLM first if a key is configured;
    any failure (network, quota, bad key) OR an empty response (confirmed
    real failure mode - see GENERATION_MAX_TOKENS's own comment: a
    reasoning model can still come back empty in edge cases even with a
    generous budget) falls back to the local Ollama model rather than
    leaving the page with no synthesis text at all."""
    if settings.synthesis_provider == "glm" and settings.glm_api_key:
        try:
            text = _call_glm(prompt)
            if text:
                return text, "glm", settings.glm_model
            logger.warning("GLM synthesis call returned empty content, falling back to Ollama")
        except Exception:
            logger.exception("GLM synthesis call failed, falling back to Ollama")
    return _call_ollama(prompt), "ollama", settings.ollama_model


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
    db.upsert_synthesis(SynthesisText(
        page_key=page_key, text=text, data_hash=new_hash, generated_at=now(), provider=provider, model=model,
    ))


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
