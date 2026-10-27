# Numeric grounding audit of the LLM paragraphs

`synthesis.py` instructs the model "use ONLY the real figures below".
`backend/src/global_monitor/verify_synthesis.py` checks whether it did: every
number in a stored paragraph is looked up in the figures that page's prompt was
built from (bloc aggregates, periods, simple ratios/differences). Read-only, no
LLM, no network. Run: `python -m global_monitor.cli verify-synthesis [--json]`.

## Results (2026-10-27)

Same 35 English bloc/compare pages, same prompts, same audit, three sources of text:

| | stored text (`qwen2.5-coder:3b`) | GLM `glm-4.5-flash`, one shot | GLM + audit-and-retry |
|---|---|---|---|
| pages with no unverified number | 9 / 35 | 28 / 35 | 35 / 35 |
| numbers that can be judged* | 446 | 675 | 666 |
| verified (grounded, loose, derived) | 376 (84.3%) | 659 (97.6%) | 666 (100%) |
| unverified | 70 (15.7%) | 16 (2.4%) | 0 |
| of which off by a power of ten | 27 | 6 | 0 |
| pages with broken decimals ("5. 467") | 3 | 0 | 0 |

\* years, bare small integers and constants in metric names (such as "$3.65/day") are set aside.

- The retry loop (at most 2 rewrites, offending numbers named in the request) fixed all 7
  pages GLM got wrong on the first try.
- GLM also writes more figures per paragraph (19 judgeable per page against 13), so the
  gap is not explained by it saying less.
- Example of what the audit caught in the stored text: the EU/US military page said the US
  spends "$95.44 billion" and the EU "$4.606 billion"; the database holds $954.4 billion and
  $460.6 billion. GLM wrote $954.4 billion and $460.6 billion.
- The first version of the audit read GLM's verbatim copies of the prompt's own `3.077e+13`
  notation as invented numbers; it now parses exponents, and these tables use that version.
- 245 translations are not audited.

The audit is wired into generation: `synthesis._verified_text` rewrites a paragraph that fails
and, if it still fails after `VERIFY_RETRIES` rewrites, keeps the previous text instead of
publishing it.

## What this does not catch

- Direction and attribution: a correct number attached to the wrong bloc or
  metric ("EU leads on X" when the US does) passes if the number exists.
- Unit-stripped numbers ("3.492" for $34.92 trillion) land in `ungrounded`, not
  `magnitude_error`, by design.
- Matching is by value, so a 3-significant-digit figure can coincide with an
  unrelated one; `magnitude_error` is limited to shifts of at most 10^3 and to
  unit classes that agree, to keep that rare.
- Both models were run once per page; the 35-page sample is small and the retry result is
  not a guarantee for future pages.
- A retry can make a model drop a fact rather than correct it; the audit only checks that the
  numbers left are in the data, not that the paragraph still says everything it should.
