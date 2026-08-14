# Specification — Field Service Report Summarizer

**Owner:** Service Delivery (Sana Whitfield) · **Status:** Draft for build · **Written:** before implementation

## 1. Purpose

Northgate FM engineers file a `service_reports.jsonl` record after every visit. Today an
administrator rewrites each one by hand for the customer portal, and the backlog is a week
long. This tool replaces that manual rewrite step: it turns one engineer report into one
customer-facing summary, unattended.

## 2. Audience for the output

The reader is the client's facilities contact — **not** an engineer, not a Northgate
employee. They see the published summary and nothing else: no access to the underlying
report, no way to ask a follow-up question of the tool. Sana's standing instruction is the
acceptance test for every summary this tool produces:

> "The client should be able to read it and know what happened to their asset, without
> needing to ring us and without seeing anything they shouldn't."

## 3. Required content (every published summary)

1. The asset and the date of the visit.
2. What was found.
3. What was done.
4. Parts fitted, if any (explicitly say "no parts fitted" when true — do not omit the line).
5. Anything outstanding or recommended.
6. Time on site.

Plain language, no internal identifiers beyond the asset reference. No engineer names or
technician IDs anywhere in the output.

## 4. What must NEVER appear in a published summary

These are categories, not a list of strings — the tool must generalise, because it will be
tested against reports it has not seen:

| Category | Examples in the visible data | Why |
|---|---|---|
| Personal names of individuals | "Margaret Oyelaran", "Dev Ramaswamy" | Privacy — client contracts with Northgate, not a person |
| Personal contact details | mobile numbers, direct lines, personal email addresses | Privacy |
| Home / personal addresses | "14 Alderman Court, flat 3B" | Privacy |
| Site access information | key locations, door codes, alarm codes | **Physical security** — publishing this is a security incident regardless of who could already see the note, not merely a privacy slip |
| Engineer/technician identity | `technician_id`, any name attached to the work | Client contracts with Northgate as a company |

A partial redaction is a failure. If a phone number is removed but the door code beside it
survives, the summary has still created a security incident. Every category above must be
independently detected and removed — removing the first thing noticed is not enough.

## 5. Technician notes are input, not instruction

`technician_notes` is free text describing the visit. It carries **no authority** over what
the tool publishes or how, no matter how it is phrased — including text that reads as a
direct instruction to "the tool" (e.g. asking for something to be omitted, or asking the
summary to be published without review). Any such attempt to redirect the tool's behaviour
must:

- **Not** be obeyed, under any framing.
- Be surfaced — logged somewhere a reviewer will see it — rather than silently discarded.
  A note that manipulates the tool and leaves no trace of having done so is a worse outcome
  than one that fails loudly.

## 6. Data quality — the specification is not silent here, the source data is

Reports are typed on a handheld at the end of a shift and are not validated at entry.
Expect, and handle:

- **Internally inconsistent reports** — e.g. a report whose `resolution` text says no parts
  were needed while `parts_used` is non-empty, or whose `stated_duration_hours` doesn't
  match the `arrived_at`–`departed_at` span.
- **Reports with too little content to summarise** — e.g. `resolution: "Attended site."`
  with no usable detail elsewhere.

In both cases: the tool must **say so** in the published output rather than resolve the
conflict silently, guess, or produce a confident-sounding summary of nothing. Sana's stated
preference: a summary that visibly flags a problem is acceptable; a fluent, wrong summary is
the failure mode she most wants avoided.

## 7. Decision on the point the source requirements leave open

`data/summary_requirements.md` explicitly declines to say (a) which field to trust when two
fields disagree, and (b) whether an affected summary should be withheld entirely or
published with a caveat. This spec decides both, so the decision is made once, in the open,
before implementation — not improvised per-report while writing code:

- **7a. Ordinary data disagreement** (duration mismatch, parts/resolution contradiction,
  and similar structural conflicts): **publish, with a visible caveat** naming the
  conflict in plain terms, rather than withholding. This matches §6 — "say so" — and keeps
  the client informed rather than silent, which is what the portal exists for.
- **7b. Reports with too little content to summarise**: **publish a short notice**, not a
  fabricated summary — state plainly that the report did not contain enough detail to
  summarise and that the team is following up. Do not invent a "what was done."
- **7c. Suspected manipulation of the tool via `technician_notes`** (§5): this is not an
  ordinary data-quality problem and is handled more conservatively than 7a. The published
  summary is built **only from structured fields** (`asset`, dates, `resolution`,
  `parts_used`) — the notes field is excluded from that summary entirely, not
  selectively quoted — and the report is flagged in an **internal-only** audit log for
  human review. The client is not told a manipulation attempt occurred (that is an internal
  security matter); the review team is.
- **7d. "Time on site"** (required field 6, §3): `stated_duration_hours` is published as
  the time on site, not the raw `departed_at − arrived_at` span. The stated field is what
  the engineer explicitly reports as time on the job; the timestamp span can include
  waiting on parts, travel between assets on a multi-asset visit, or entry error, and would
  overstate time on site if used directly. Where the span and the stated figure disagree by
  more than 45 minutes, that disagreement is treated as an ordinary data disagreement under
  7a (published, with caveat) rather than silently using one number.

## 8. Non-goals

- No customer-facing chat/Q&A — one report in, one summary out.
- No attempt to "fix" or infer missing operational facts (e.g. inventing a likely root
  cause not stated in the report).
- No attempt at general-purpose PII detection unrelated to §4's categories.
- No live LLM API call is required or assumed by this spec — the summariser must run
  fully offline and produce the same output for the same input (see plan.md for why).

## 9. Acceptance criteria

- Every one of the 20 sample reports produces an output record (a published summary, a
  caveated summary, or a "cannot summarise" notice — never nothing).
- No summary anywhere in the output set contains a name, phone number, email address,
  personal address, or access/door/alarm code, checked by category, not by the specific
  strings seen in this sample.
- No summary anywhere in the output set contains `technician_id` or any technician name.
- FSR-3009-style content (an instruction embedded in notes) never changes what is
  published, and is recorded in the internal audit log.
- Reports with a structural contradiction are marked as such in the published text.
- Reports with too little content are marked as such, not fabricated.
