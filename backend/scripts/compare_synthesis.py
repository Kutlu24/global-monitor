"""Regenerate every bloc/compare paragraph with GLM and audit it with
verify_synthesis, in two arms, next to the stored paragraphs as baseline:

  glm        one shot, same prompt synthesis.py uses
  glm+retry  same, but a paragraph with unverified numbers is sent back (up to
             MAX_RETRIES) with the offending numbers listed

Read-only against the database: nothing is written back. Needs GLM_API_KEY in
the environment (or .env). Usage, from backend/:

    python scripts/compare_synthesis.py [--out results.json]
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from global_monitor import db, verify_synthesis as vs
from global_monitor.config import settings
from global_monitor.models import SynthesisText
from global_monitor.synthesis import _COMPARE_PAIRS, _DIMENSIONS, _bloc_prompt, _call_glm, _compare_prompt

MAX_RETRIES = 2
API_ATTEMPTS = 4  # per call: rate limits and transient network errors get a backoff, then give up


def _prompts() -> dict[str, str]:
    blocs = {b.bloc_id: b for b in db.get_blocs()}
    out = {f"bloc:{b.bloc_id}": _bloc_prompt(b) for b in blocs.values()}
    for a, b in _COMPARE_PAIRS:
        if a in blocs and b in blocs:
            out[f"compare:{a}-vs-{b}"] = _compare_prompt(blocs[a], blocs[b])
            for d in _DIMENSIONS:
                out[f"compare:{a}-vs-{b}:{d}"] = _compare_prompt(blocs[a], blocs[b], d)
    return out


def _glm(prompt: str) -> str | None:
    """One GLM call with backoff. Returns None after API_ATTEMPTS failures (or an
    empty reply) so the caller can skip the page instead of crashing the run."""
    for attempt in range(API_ATTEMPTS):
        try:
            text = _call_glm(prompt)
            if text:
                return text
            print("  empty reply", file=sys.stderr, flush=True)
        except Exception as e:  # openai raises several types (rate limit, connection, auth)
            print(f"  GLM call failed ({type(e).__name__}: {str(e)[:120]})", file=sys.stderr, flush=True)
            if "auth" in type(e).__name__.lower() or "401" in str(e):
                raise SystemExit("GLM rejected the key; stopping instead of retrying.")
        time.sleep(5 * 2 ** attempt)
    return None


def _save(path: str, arms: dict, texts: dict, skipped: list) -> None:
    """Rewritten after every page so an interrupted run keeps its progress."""
    summary = {arm: vs.summarize(rs) for arm, rs in arms.items() if rs}
    with open(path, "w") as f:
        json.dump({"summary": summary, "skipped": skipped, "texts": texts}, f, indent=2, ensure_ascii=False)


def _audit(page_key: str, text: str, model: str):
    row = SynthesisText(page_key=page_key, text=text, data_hash="", generated_at="", provider="glm", model=model)
    return vs.verify_page(row)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="synthesis_comparison.json")
    args = ap.parse_args()
    if not settings.glm_api_key:
        raise SystemExit("GLM_API_KEY is not set in this process (environment or global-monitor/.env).")

    baseline = {r.page_key: r for r in db.list_synthesis() if "|" not in r.page_key}
    arms: dict[str, list] = {"baseline": [], "glm": [], "glm+retry": []}
    texts: dict[str, dict] = {}
    skipped: list[str] = []
    try:
        for page_key, prompt in _prompts().items():
            draft = _glm(prompt)
            report = _audit(page_key, draft, "glm") if draft else None
            if report is None:
                skipped.append(page_key)
                print(f"{page_key}: SKIPPED", flush=True)
                _save(args.out, arms, texts, skipped)
                continue
            # Baseline only for pages GLM also produced, so the arms compare like with like.
            if page_key in baseline and (b := vs.verify_page(baseline[page_key])):
                arms["baseline"].append(b)
            arms["glm"].append(report)
            texts[page_key] = {"glm": draft}
            one_shot_clean = report.clean
            for _ in range(MAX_RETRIES):
                if report.clean:
                    break
                retry = _glm(vs.feedback_prompt(prompt, draft, report))
                if not retry:
                    break
                draft = retry
                report = _audit(page_key, draft, "glm") or report
            arms["glm+retry"].append(report)
            texts[page_key]["glm+retry"] = draft
            print(f"{page_key}: one-shot {'ok' if one_shot_clean else 'BAD'}, "
                  f"retry {'ok' if report.clean else 'BAD'}", flush=True)
            _save(args.out, arms, texts, skipped)
    except KeyboardInterrupt:
        print("interrupted; partial results kept", file=sys.stderr)
    _save(args.out, arms, texts, skipped)
    print(json.dumps({arm: vs.summarize(rs) for arm, rs in arms.items() if rs}, indent=2))
    print(f"wrote {args.out}; {len(skipped)} page(s) skipped")


if __name__ == "__main__":
    main()
