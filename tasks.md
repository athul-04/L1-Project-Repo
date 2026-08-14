# Tasks — build order

Each task is independently testable before moving to the next. Order matters: redaction and
detection are built and tested in isolation before the composer wires them together, so a
bug in composition can't hide inside an untested redaction rule.

1. **`redaction.py` — EMAIL, PHONE categories.**
   Regex-based. Test: emails and UK mobile/landline formats seen in the sample data are
   removed; surrounding text is untouched.
2. **`redaction.py` — ACCESS_CODE category.**
   Context-triggered ("code", "key held", "access") rather than digit-pattern alone, since a
   bare number can't be safely distinguished from any other number in isolation. Test:
   FSR-3003's plant-room code is removed; a stated duration or part number is not.
3. **`redaction.py` — ADDRESS category.**
   Token-based (flat/court/street/road/lane/close/drive + house number). Test: FSR-3003's
   address is removed.
4. **`redaction.py` — NAME category.**
   Context-triggered on phrases like "contact is", "manager", "spoke to", "ask for",
   followed by a capitalised two-to-three-word sequence. Test: both named individuals in the
   sample (FSR-3003, FSR-3014) are removed; asset names like "Chiller CH-04" are not, since
   they don't follow a person-context trigger.
5. **`redaction.py` — combine into one `redact(text) -> (clean_text, categories_removed)`
   entrypoint.** Test: a string containing all four categories at once has all four removed,
   not just the first match (this is the "partial redaction" failure spec.md §4 calls out).
6. **`detect.py` — contradiction check.**
   parts_used non-empty vs. resolution asserting no parts; stated_duration_hours vs.
   timestamp span beyond 45 minutes. Test against FSR-3005, FSR-3006, and both a positive
   and negative invented variant in different wording.
7. **`detect.py` — insufficient-data check.**
   Resolution below a length/information threshold and no usable content in redacted notes.
   Test against FSR-3007, FSR-3008, and a report that's short but genuinely informative
   (should NOT trip the check) to guard against a too-aggressive threshold.
8. **`detect.py` — injection-attempt check.**
   Notes containing second-person imperatives directed at "the tool"/"summary"/similar, or
   instructions about what to publish/omit. Test against FSR-3009 and at least one
   differently-worded invented variant, plus a genuine recommendation sentence
   (e.g. FSR-3002's "recommend replacement at next PM visit") as a negative case — the check
   must not fire on ordinary recommendations.
9. **`summarizer.py` — template composer.**
   Given a report + redaction result + detection flags, produce the six required fields
   (spec.md §3) as the normal case. Test against a clean report (FSR-3001).
10. **`summarizer.py` — caveat and notice paths.**
    Wire in §7a (caveat), §7b (notice), §7c (structured-fields-only + audit log entry).
    Test against FSR-3006 (caveat), FSR-3007/3008 (notice), FSR-3009 (structured-only +
    audit log entry present).
11. **`summarizer.py` — CLI + batch run.**
    Read `data/service_reports.jsonl`, write `output/summaries.md` and
    `output/audit_log.json`. Test: 20 reports in, 20 output records out, none silently
    dropped.
12. **End-to-end run over all 20 sample reports.** Manually read every output against
    spec.md §9's acceptance criteria — this is the step that catches what unit tests miss,
    since the held-out set changes wording, not categories.
13. **AI output review** (intent, tests, security, performance, maintainability) —
    documented separately in `docs/REVIEW.md`, done after the implementation is working,
    not before.
