# Numeric grounding audit of the LLM paragraphs

`synthesis.py` instructs the model "use ONLY the real figures below".
`backend/src/global_monitor/verify_synthesis.py` checks whether it did: every
number in a stored paragraph is looked up in the figures that page's prompt was
built from (bloc aggregates, periods, simple ratios/differences). Read-only, no
LLM, no network. Run: `python -m global_monitor.cli verify-synthesis [--json]`.

## Result on the production DB (2026-10-27)

All 35 English bloc/compare paragraphs were written by `ollama / qwen2.5-coder:3b`
(the fallback; no GLM key was set when they were generated). The 245 translations
are not audited here.

| | count |
|---|---|
| paragraphs | 35 |
| paragraphs with no unverified number | 7 (20%) |
| numbers extracted | 542 |
| set aside (years, bare small integers, constants in metric names) | 90 |
| numbers that can be judged | 452 |
| grounded / loose / derived | 324 / 6 / 39 (81.6%) |
| magnitude error (right digits, wrong power of ten) | 27 |
| ungrounded (no counterpart in the prompt) | 56 |
| paragraphs with broken decimals ("5. 467") | 3 |
| paragraphs whose underlying data changed since generation (stale) | 7 |

Example: the EU/US military page says the US spends "$95.44 billion" and the EU
"$4.606 billion"; the database holds $954.4 billion and $460.6 billion.

## What this does not catch

- Direction and attribution: a correct number attached to the wrong bloc or
  metric ("EU leads on X" when the US does) passes if the number exists.
- Unit-stripped numbers ("3.492" for $34.92 trillion) land in `ungrounded`, not
  `magnitude_error`, by design.
- Matching is by value, so a 3-significant-digit figure can coincide with an
  unrelated one; `magnitude_error` is limited to shifts of at most 10^3 and to
  unit classes that agree, to keep that rare.
- Only a 3B local model was audited. The GLM path is untested here.
