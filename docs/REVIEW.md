# AI Output Review

This is a review of the AI-generated implementation (commit `04-implement`), done after it
was working and passing its own tests — not before, per `tasks.md` task 13. Two real issues
were found and corrected; both are recorded here with the report id evidence that surfaced
them, per the checklist's evidence standard, and both are covered by a regression test
committed alongside the fix.

## 1. Intent

**Checked against:** spec.md §3 (six required fields) and §9 (acceptance criteria).

**Issue found — generic resolution on multi-asset reports (real, fixed).**
`FSR-3011` is the longest and highest-value report in the sample: a full annual inspection
across six assets. Its `resolution` field is a one-line summary ("Full plant inspection and
multiple remedial actions across six assets") while the actual findings — which contactor
was pitted, which sensor was open-circuit, which gasket had perished — live in
`technician_notes`. The first-pass composer only ever read `resolution` for "what was found
/ done," so the published summary for the highest-effort visit in the dataset was also the
least informative one, despite the real detail being available and safe to publish (no PII
in that report). This directly fails spec.md §3 items 2–3 for that report even though every
unit test passed, because no test exercised a report where `resolution` and
`technician_notes` diverge this much in richness.

**Fix:** `_found_done_text()` — when `resolution` is short and notes are substantially
richer, notes content is folded into "what was found / done" (excluding the sentences
already destined for "Outstanding," to avoid duplicating the follow-up recommendation).
**Evidence:** before the fix, FSR-3011's published "What was found / done" line was nine
words long and mentioned no specific asset; after the fix it names all seven parts
individually with what was found on each. Regression test:
`test_generic_resolution_expanded_with_notes_detail_on_long_multi_asset_report`.

**Checked and not changed:** the checklist specifically asks whether the final
recommendation on the longest report survives intact. It does — "30 days" and "the same
batch" both appear in the published Outstanding line — verified directly in
`output/summaries.md` and asserted in the same test.

## 2. Tests

32 unit tests across `test_redaction.py`, `test_detect.py`, `test_summarizer.py`, plus one
end-to-end batch test asserting 20 reports in, 20 output records out with no silent drops.
Every redaction category and every detection rule has at least one test using wording that
does **not** appear in `data/service_reports.jsonl` (e.g. "alarm code is 8842" vs. the
sample's "access code for the plant room is 4471"), because the grading set is held-out —
a test suite that only replays the sample's exact strings would prove nothing about
generalisation. Negative cases are included deliberately: a genuine recommendation sentence
(FSR-3002 style) must **not** trip the injection detector, and a short-but-informative
resolution must **not** trip the insufficient-data detector — both guard against the
detectors being too aggressive, which is as much a failure mode as being too weak.

**Gap acknowledged, not closed:** there is no test asserting the tool's behaviour on a
malformed JSON line or a report missing a required key entirely (e.g. no `arrived_at`).
`run_batch` would currently raise and stop the whole batch rather than skip and continue.
Left as a known limitation rather than fixed under time pressure — noted here rather than
silently, per the review discipline this task asks for.

## 3. Security

**Checked against what the tool publishes, not just how the code reads** — per the brief's
explicit instruction and the checklist's self-check question.

**Issue found — resolution field not redacted (real, fixed, most significant finding).**
The redaction pass was wired to run on `technician_notes` only. `resolution` is also free
text typed by a technician under time pressure, and nothing in the data schema prevents the
same categories — a name, a phone number, an access code — from ending up there instead of
in notes on a report I haven't seen. Before the fix, a synthetic report with a phone number
and access code embedded in `resolution` (see
`test_pii_in_resolution_field_is_also_redacted`) published both straight through, because
the composer read `report['resolution']` directly rather than through `redaction.redact()`.
This is exactly the "partial redaction" failure mode spec.md §4 calls out, except at the
field level rather than within a single string. **Fix:** `resolution` now goes through the
same `redact()` call as `technician_notes` before any use, including in the injection-path
and contradiction-caveat output.

**Checked, held:** the FSR-3009 prompt-injection case (§5, §7c). Verified directly against
`output/audit_log.json` — the report is flagged `INJECTION_ATTEMPT`, and its published text
in `output/summaries.md` contains only the structured fields (asset, resolution, parts,
time), with the manipulative note's requested framing ("no issues found") absent.
`docs/ANALYSIS.md` covers this report specifically, including whether the attempt would be
visible to anyone — it is, in the audit log, which is the "would anyone know" test the
checklist asks.

**Checked, held:** "partial redaction" — `redaction.redact()` computes the full category
set from all rule matches *before* merging overlapping spans (see the comment in
`_merge_overlaps`), specifically so that a category isn't lost from the audit trail just
because its span happened to be absorbed into a wider one during text replacement.
`test_all_categories_in_one_string_all_removed` asserts all five categories are removed
from a single string containing all of them at once, not just the first one matched.

## 4. Performance

The tool processes 20 reports (and would process thousands) in well under a second — it's
regex matching and string templating over short text fields, not a bottleneck at any
realistic Northgate FM report volume. No performance issue found; no premature optimisation
added. `_ADDRESS_RE` and `_ACCESS_CONTEXT_RE` were checked by hand for catastrophic
backtracking risk (no nested quantifiers over the same character class) since regex
performance failures are usually invisible until a pathological input arrives — none of the
patterns here have that shape.

## 5. Maintainability

Each module has one job (`redaction.py` never decides what to publish; `detect.py` never
rewrites text; `summarizer.py` composes and never invents facts) per `plan.md`'s
architecture section, which made both fixes above localised — the resolution-redaction fix
touched one call site and did not require changes to `redaction.py` itself, because the
category rules were already field-agnostic. `_RECOMMEND_KEYWORDS` and the various
thresholds (`DURATION_MISMATCH_THRESHOLD_HOURS`, `_EXPAND_IF_RESOLUTION_WORDS_UNDER`, etc.)
are named module-level constants rather than inline magic numbers, specifically so the next
person tuning them against the held-out set doesn't have to read the regex to find them.
