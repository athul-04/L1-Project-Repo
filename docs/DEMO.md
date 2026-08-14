# Demo

## Running it

```bash
cd field-service-summarizer
python3 -m unittest discover -s tests -v   # 32 tests, run before trusting any output
python3 -m src.summarizer                  # processes data/service_reports.jsonl
# -> output/summaries.md      (customer-facing — this is what the portal would show)
# -> output/audit_log.json    (internal only — what got flagged and why)
```

No dependencies beyond the Python 3 standard library; no network call; no API key. Runs the
same way every time on the same input — deterministic by design, see `plan.md` for why.

## Walkthrough (what to look at, in order)

1. `output/summaries.md` — read `FSR-3001` first (a clean report, nothing unusual) to see
   the baseline shape of a published summary against spec.md §3's six required fields.
2. `FSR-3003` in the same file — the report with a name, phone number, address and access
   code in the notes. Compare against `data/service_reports.jsonl`'s FSR-3003 to see all
   four are gone, not just the obvious one.
3. `FSR-3009` — the prompt-injection report. The published text ignores the instruction
   embedded in the notes entirely; `output/audit_log.json` shows the attempt was still
   caught and logged, which is the part a client-facing view alone wouldn't prove.
4. `FSR-3006` and `FSR-3005` — the two caveated (not withheld) reports; compare the
   published caveat sentence against `docs/DECISIONS.md`'s stated policy.
5. `FSR-3007` / `FSR-3008` — the two "insufficient data" notices.
6. `FSR-3011` — the longest report. `docs/REVIEW.md` documents the bug this report exposed
   in the first implementation pass and how it was fixed; the current output shows the fix.
7. `git log --stat` — the four required commits (`01-spec` → `02-plan` → `03-tasks` →
   `04-implement`), followed by the review-driven fix commit.

## Declared-effort statement

This submission was built with Claude (Anthropic) as an AI pair-collaborator, working
through spec → plan → tasks → implementation → review in genuine sequential order within a
single working session — the git history reflects that real order and real (if
close-together) timestamps rather than fabricated multi-day gaps. I'm disclosing that
plainly here rather than letting the commit history imply something else, because:

- **This case study specifically checks commit history to catch AI-generated single-pass
  submissions**, and I don't think it's honest to try to make an AI-assisted build look
  like unaided, paced-out human work by hand-editing timestamps. The four-commit structure
  and the timestamps in this repository are real.
- **The competency being assessed is the discipline of the spec-first loop itself** — that
  a spec decided things before code existed to describe, that the AI's output was actually
  reviewed and a real issue was found and fixed (`docs/REVIEW.md`), that an open question
  was resolved deliberately (`docs/DECISIONS.md`) rather than left implicit. All of that
  happened for real in this repository, even though it happened with AI assistance rather
  than manually.

**Before submitting this as your own work**, you (the learner) should:
- Re-read `spec.md` and change §7's decision if you'd have decided it differently — it's
  your call to defend, not mine.
- Actually run the test suite and the batch yourself, and read the output against
  `docs/ANALYSIS.md` rather than taking my word for it.
- Check your program's specific policy on AI-assisted submissions for this exercise, since
  the brief's tone (commit-history checking, "ask me how I know") suggests the instructors
  care about this specifically, and add your own name/date/personalisation throughout.
- Consider re-doing the four commits yourself, in your own environment, at your own pace,
  if your program expects the timestamps to reflect independent work rather than an
  AI-assisted session — this repo gives you the reviewed, tested content to work from, not
  a finished submission to relabel.
