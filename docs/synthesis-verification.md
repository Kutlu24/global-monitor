# Numeric grounding audit of the LLM paragraphs

`synthesis.py` instructs the model "use ONLY the real figures below".
`backend/src/global_monitor/verify_synthesis.py` checks whether it did: every
number in a stored paragraph is looked up in the figures that page's prompt was
built from (bloc aggregates, periods, simple ratios/differences). Read-only, no
LLM, no network. Run: `python -m global_monitor.cli verify-synthesis [--json]`.

## Results (2026-10-27)

Same 35 English bloc/compare pages, same prompts, same audit, three sources of text. The first
column is the *development* database on the author's workstation, whose paragraphs were written by
the local fallback model; it is not what the live site served (see "Production" below).

| | dev-DB text (`qwen2.5-coder:3b`) | GLM `glm-4.5-flash`, one shot | GLM + audit-and-retry |
|---|---|---|---|
| pages with no unverified number | 9 / 35 | 28 / 35 | 35 / 35 |
| numbers that can be judged* | 446 | 675 | 666 |
| verified (grounded, loose, derived) | 376 (84.3%) | 659 (97.6%) | 666 (100%) |
| unverified | 70 (15.7%) | 16 (2.4%) | 0 |
| of which off by a power of ten | 27 | 6 | 0 |
| pages with broken decimals ("5. 467") | 3 | 0 | 0 |

\* years, bare small integers and constants in metric names (such as "$3.00/day") are set aside.

- The retry loop (at most 2 rewrites, offending numbers named in the request) fixed all 7
  pages GLM got wrong on the first try.
- GLM also writes more figures per paragraph (19 judgeable per page against 13), so the
  gap is not explained by it saying less.
- Example of what the audit caught in the dev-DB text: the EU/US military page said the US
  spends "$95.44 billion" and the EU "$4.606 billion"; the database holds $954.4 billion and
  $460.6 billion. GLM wrote $954.4 billion and $460.6 billion.
- The first version of the audit read GLM's verbatim copies of the prompt's own `3.077e+13`
  notation as invented numbers; it now parses exponents, and these tables use that version.
- 245 translations are not audited.

The audit is wired into generation: `synthesis._verified_text` rewrites a paragraph that fails
and, if it still fails after `VERIFY_RETRIES` rewrites, keeps the previous text instead of
publishing it.

## Production

The live container's database already held GLM text (`glm-4.5-flash`) for all 35 English pages,
written before the audit existed. Audited with the same code: 25 / 35 pages clean, 733 of 759
judgeable numbers verified (96.6%), 26 unverified (9 off by a power of ten). That matches the
one-shot GLM column above, not the local-model one.

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

## Auditing the translations

`python -m global_monitor.cli verify-translations [--json]` checks every `page_key|lang`
row against the English row of the same page (read-only, no LLM). It reads scale words in
each language (trilyon, Milliarden, 万亿, трлн, "miles de millones") so a correct
conversion is not flagged, and reports: `scale_diff` (same digits, different power of ten:
Spanish "billón" for 10^9, a dropped "trillion", Chinese 亿 for 10^9), `changed` (a figure
no English number explains), `dropped` (an English figure missing), `wrong_script`,
`same_as_en`, `truncated` and `stale`.

Result on the production database, 2026-10-28 (322 translation rows):

| Provider | Rows | With a serious finding | Altered or mis-scaled figures | Truncated |
|---|---|---|---|---|
| glm-4.5-flash | 198 | 31 (16%) | 17 | 18 |
| gemma2:2b | 124 | 55 (44%) | 51 | 10 |

"Serious" is any of scale_diff, changed, truncated, wrong_script, same_as_en. A further 28
rows only omit a figure, which is reported but not counted. Chinese and Arabic are worst
for both providers. The check is a heuristic: a figure rewritten in prose ("a third")
shows up as dropped, and `dropped` is noisier than the other findings.

The English side has the same gap: two published paragraphs end mid-sentence
(`compare:eu-vs-us:social`, `tension:bloc:usmca`), which the number audit cannot see.

## The generation gate now covers both gaps

- **Complete sentences.** `_is_complete` rejects a paragraph that does not end in a sentence
  terminator. A reasoning model that runs out of `GENERATION_MAX_TOKENS` returns cut-off text
  with no error, so the gate treats it like a failed number check: up to `VERIFY_RETRIES`
  rewrites ("stopped mid-sentence" prompt), and the paragraph is not stored if it stays cut off.
- **Translations.** `_translate` runs `verify_translations.audit_translation` on every new
  translation before it is stored. A serious finding sends the text back for a rewrite (up to
  `VERIFY_RETRIES`); a translation that still fails is not stored, so the page falls back to
  English instead of showing a wrong figure. The translation prompt states that billion is
  10^9 and trillion is 10^12.
- Tests: `tests/test_synthesis_gate.py`.

Repairing existing rows: marking a row's `data_hash` as stale makes the next
`generate_translations()` rebuild it through this gate. In production a small fallback model
(`gemma2:2b`) often fails the gate for Chinese, Arabic and French; those rows stay stale-marked
rather than being published wrong.

A stale-marked row is still served (`_synthesis_payload` falls back to English only when the
row is missing). Rows that could not be repaired were therefore deleted in production
(37 rows, 2026-10-28), so those pages show English until a later run passes the gate.

## Tension pages (GDELT)

The English text of `tension:*` pages is rewritten every two hours because its figures move, and
each rewrite makes the stored translations stale. They are retranslated in the same cycle. If a
retranslation fails the gate while the stored translation still belongs to the old figures,
`_translate_or_drop` deletes that row, so the page serves the English text instead of a
translation of numbers that no longer match. A translation that is current is never deleted.
