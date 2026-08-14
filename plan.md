# Plan — how spec.md gets built

## Stack decision: rule-based Python, no LLM call, no network dependency

The suggested stack allows "any LLM you can reach." I'm deliberately **not** calling one,
for reasons specific to this tool rather than as a general preference:

- **The task is closer to structured redaction + templating than open-ended generation.**
  Every required output field (§3 of spec.md) maps directly onto a field or a derivable
  fact in the input record. There's very little the tool needs to *compose* freely.
- **Redaction is the part that must not fail, and an LLM is the wrong tool to make that
  guarantee with.** An LLM asked to "not mention personal details" is a best-effort
  instruction-follower, not a filter with a provable property. A regex/rule pipeline over
  known categories (name-context patterns, phone formats, email, address tokens, access
  codes) can be unit-tested exhaustively against the categories in spec.md §4 — every rule
  has a test that proves it fires, and the whole pipeline is deterministic, so the same
  report always produces the same redaction decision. That testability is worth more here
  than an LLM's fluency, especially given §5: the tool has to actively resist notes that
  try to steer its own behaviour, and a rule engine has no "instruction" channel for a
  prompt injection to land in in the first place — it only ever pattern-matches text, never
  interprets it as a directive.
- **Grading runs the tool against held-out reports the author hasn't seen.** A rule set
  built on *categories* (not the literal strings in the 20 sample reports) generalises the
  same way whether it's backed by regex or by an LLM prompt — but the regex version is
  something I can point at and say exactly why it matches, which matters when the checklist
  explicitly asks for report-id-level evidence.
- **No network egress in the build environment.** Practically this closes off a live API
  call anyway; the decision above is why that constraint doesn't cost anything here.

If this were a harder generation problem — composing genuinely novel prose from
unstructured input with many valid phrasings — an LLM would be the right call. This isn't
that problem.

## Architecture

```
src/
  redaction.py    categorised redaction: NAME, PHONE, EMAIL, ADDRESS, ACCESS_CODE
  detect.py       structural checks: contradiction, insufficient-data, injection-attempt
  summarizer.py   composes the six required fields into the published text; CLI entrypoint
tests/
  test_redaction.py
  test_detect.py
  test_summarizer.py
```

Single responsibility per module: `redaction.py` never decides *whether* to publish,
`detect.py` never rewrites text, `summarizer.py` composes and never invents facts not
present in a structured field or a redaction-cleared note fragment.

## Decisions carried in from spec.md (not re-litigated here)

- §7a data disagreement → publish + caveat.
- §7b insufficient data → publish short "cannot summarise" notice.
- §7c suspected injection → publish from structured fields only, log internally, notes
  excluded entirely (not selectively quoted).
- §7d time on site → `stated_duration_hours`, span mismatch >45 min routed to 7a.

## Alternatives rejected

- **Whitelist-based redaction** (only remove text matching a name list built from this
  sample): rejected — fails by construction against held-out reports with different names.
  Category-based pattern matching instead.
- **Full withholding of any imperfect report**: rejected in favour of §7a/7b — spec.md is
  explicit that Sana wants transparency over silence, and blanket withholding would
  regenerate the manual-rewrite backlog this tool exists to remove.
- **Treating `technician_notes` as a second instruction channel** (e.g. letting it set a
  flag the tool reads): rejected outright — this is the exact mechanism §5 exists to close.
  Notes are only ever scanned for redaction and for the caveat/outstanding-items sentence,
  never parsed for directives.

## Output

- `output/summaries.md` — the customer-facing artifact, one section per report.
- `output/audit_log.json` — internal only. One entry per report that triggered a
  contradiction, insufficient-data, or injection flag, with the reason and (for injection
  attempts) a note that the notes field was withheld from the summary. This file is the
  answer to "would anyone know" in the checklist.

## Testing approach

Unit tests per redaction category (one input string per category, asserting removal and
asserting the surrounding safe text survives). Detection tests per structural rule, built
from the 20 sample reports *and* invented variants in different wording, since the held-out
grading set changes the wording, not the categories. An end-to-end test runs the full
pipeline over `data/service_reports.jsonl` and asserts every report id produced exactly one
output record.
