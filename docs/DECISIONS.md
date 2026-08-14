# Documented decision: the point the specification leaves open

`data/summary_requirements.md` states explicitly that it does not say:

1. Which field to trust when two fields in a report disagree.
2. Whether an affected summary should be withheld entirely, or published with a caveat.

This is decided in `spec.md` §7, before implementation, so the decision is made once and
applied consistently rather than improvised per-report while writing code. Reproduced here
as a standalone deliverable per the submission checklist.

## The decision

**Publish with a caveat. Do not withhold.**

- **Ordinary structural disagreement** (a duration mismatch, a parts/resolution
  contradiction): publish everything that is known to be true, plus a plain-language
  caveat sentence naming that something doesn't add up internally. Applied to FSR-3005 and
  FSR-3006 — see `docs/ANALYSIS.md`.
- **Reports with too little content to summarise**: publish a short, honest notice instead
  of a summary — not a withheld report, not a fabricated one. Applied to FSR-3007 and
  FSR-3008.
- **"Time on site"**: `stated_duration_hours` is the published figure, not the raw
  timestamp span, because it's the field the engineer explicitly reports as time on the
  job — the timestamp span can include waiting on parts or travel between assets and would
  overstate time on site. Where the two differ by more than 45 minutes, that disagreement
  is itself treated as an ordinary structural disagreement (published + caveated), not
  silently resolved by picking one number without comment.
- **Exception — suspected manipulation of the tool via technician notes**: this is handled
  more conservatively than an ordinary disagreement. The summary is built from structured
  fields only, the notes field is withheld from the summary entirely, and the report is
  logged for human review. This is not really "withhold vs. caveat" — it's a distinct,
  narrower case, and is called out separately in spec.md §7c precisely so it isn't
  conflated with ordinary data-quality problems.

## Why this way, not the alternative

The source requirements say Sana "would far rather publish 'this report is incomplete, we
are following up' than a confident summary that turns out to be wrong" — that's a
statement about *confidence*, not about *silence*. A blanket withhold-on-any-imperfection
policy would regenerate exactly the backlog this tool exists to remove: nearly every report
in the sample has *some* minor imperfection (see the FSR-3007/FSR-3008 rounding differences
in `detect.py`, deliberately given a tolerance so they don't trip the same flag as a
genuine problem). Publishing with a caveat keeps the client informed — which is what the
portal is for — while still being honest about what isn't certain, which is the actual
standard set by "the client should be able to read it and know what happened to their
asset... without seeing anything they shouldn't." A withheld report tells the client
nothing; a caveated one tells them the truth, including the part of the truth that is "we
're not fully sure about X."

## Where this is applied consistently

Every report that hits a structural-disagreement or insufficient-data condition in the
20-report sample gets the same treatment — see `output/audit_log.json` for the full list of
flagged reports and `output/summaries.md` for what was actually published for each. The
same rule, not a per-report judgement call, decides the outcome; `src/detect.py` and
`src/summarizer.py` implement it identically regardless of which report triggers it, which
is what makes it possible to state the policy in one paragraph and have it hold for reports
not yet seen (the held-out grading set).
