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


