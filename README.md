# Field Service Report Summarizer — Northgate FM (synthetic)

L1 AI-Augmented SDLC capstone, Option 4, case: *Field Service Report Summarizer —
Manufacturing*.

Turns engineer field reports (`data/service_reports.jsonl`) into client-portal-ready
summaries, while keeping personal and site-security information out of the customer-visible
output, refusing to fabricate confident summaries of incomplete reports, and refusing to let
technician notes act as instructions to the tool.

## Where everything is

| What | Where |
|---|---|
| Specification (written before code) | `spec.md` |
| Build plan | `plan.md` |
| Task breakdown | `tasks.md` |
| Implementation | `src/` |
| Tests (32, all passing) | `tests/` |
| Published output for all 20 reports | `output/summaries.md` |
| Internal-only flag log | `output/audit_log.json` |
| Analysis of the problem reports | `docs/ANALYSIS.md` |
| AI output review (5 lenses, issues found + fixed) | `docs/REVIEW.md` |
| The open-spec decision, documented | `docs/DECISIONS.md` |
| Demo walkthrough + declared-effort statement | `docs/DEMO.md` |
| Required 4-commit process evidence | `git log --stat` (see below) |

## Quickstart

```bash
python3 -m unittest discover -s tests   # 32 tests
python3 -m src.summarizer               # writes output/summaries.md + output/audit_log.json
```

Pure standard library, no network call, deterministic output.

## Process evidence

```
git log --stat --format="%h %ad %s" --date=iso
```

Four required commits, in order, no source file before `04-implement`:

1. `01-spec` — `spec.md` only
2. `02-plan` — adds `plan.md`
3. `03-tasks` — adds `tasks.md`
4. `04-implement` — adds `src/`, `tests/`

Followed by one review-driven fix commit (expected and documented per `starter/PROCESS.md`
— see `docs/REVIEW.md` for what it fixed and why).

Read `docs/DEMO.md` first — it includes an important disclosure about how this repository
was built and what you should do before submitting it as your own work.
