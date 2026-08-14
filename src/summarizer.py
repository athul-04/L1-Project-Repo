"""Compose the customer-facing summary for one report, and the CLI batch entrypoint.

Field mapping is spec.md §3:
  1. asset + date        -> report['asset'], report['arrived_at']
  2. what was found       -> derived from resolution / notes (see _what_was_found)
  3. what was done        -> report['resolution']
  4. parts fitted         -> report['parts_used']
  5. outstanding/recommended -> extracted from redacted notes (safe fragment only)
  6. time on site         -> report['stated_duration_hours']  (spec.md §7d)
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from . import detect, redaction

_RECOMMEND_KEYWORDS = (
    "recommend",
    "follow-up",
    "follow up",
    "monitor",
    "outstanding",
    "review",
    "next visit",
    "next pm",
)


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _split_notes_by_purpose(clean_notes: str) -> tuple[list[str], list[str]]:
    """Split ALREADY-REDACTED notes into (recommend_sentences, other_sentences). Never
    called on raw notes, and never called at all on a report that failed the injection
    check (see build_summary)."""
    if not clean_notes:
        return [], []
    recommend, other = [], []
    for s in _split_sentences(clean_notes):
        (recommend if any(k in s.lower() for k in _RECOMMEND_KEYWORDS) else other).append(s)
    return recommend, other


# A generic top-line resolution ("Full plant inspection and multiple remedial actions
# across six assets") is common on multi-asset visits and, on its own, fails spec.md §3's
# "what was found / what was done" requirement even though the real per-asset detail is
# sitting right there in the (safe, redacted) notes. Expand into it rather than discard it,
# but only the sentences NOT already destined for "Outstanding" — see build_summary.
_EXPAND_IF_RESOLUTION_WORDS_UNDER = 15
_EXPAND_IF_NOTES_WORDS_OVER = 25


def _found_done_text(resolution: str, other_sentences: list[str]) -> str:
    resolution = resolution or "Not recorded."
    if (
        other_sentences
        and len(resolution.split()) < _EXPAND_IF_RESOLUTION_WORDS_UNDER
        and sum(len(s.split()) for s in other_sentences) > _EXPAND_IF_NOTES_WORDS_OVER
    ):
        return resolution.rstrip(".") + ". " + " ".join(other_sentences)
    return resolution


def _format_date(iso_ts: str) -> str:
    try:
        return datetime.fromisoformat(iso_ts).strftime("%d %b %Y")
    except (ValueError, TypeError):
        return iso_ts or "unknown date"


def _format_parts(parts: list[str]) -> str:
    if not parts:
        return "No parts fitted."
    return "Parts fitted: " + ", ".join(parts) + "."


def _format_hours(hours) -> str:
    try:
        h = float(hours)
    except (TypeError, ValueError):
        return "not recorded"
    whole = int(h)
    minutes = round((h - whole) * 60)
    if whole and minutes:
        return f"{whole}h {minutes}m"
    if whole:
        return f"{whole}h"
    return f"{minutes}m"


def build_summary(report: dict) -> dict:
    """Returns a dict describing the outcome for one report:
    {
      report_id, status: 'published' | 'caveated' | 'insufficient',
      published_text, internal_flags: [str, ...]
    }
    `internal_flags` is never written into published_text.
    """
    report_id = report.get("report_id", "UNKNOWN")
    asset = report.get("asset", "Unknown asset")
    date = _format_date(report.get("arrived_at", ""))
    raw_notes = report.get("technician_notes", "") or ""

    internal_flags: list[str] = []

    # `resolution` is also free text typed by a technician, not a controlled field — the
    # same categories that turn up in `technician_notes` (spec.md §4) could land here on a
    # report we haven't seen, so it goes through the same redaction pass. Found during
    # review: the first pass only redacted `technician_notes` and published `resolution`
    # verbatim everywhere, which would leak PII/access info straight through on any report
    # that put it in the "wrong" field. See docs/REVIEW.md.
    raw_resolution = report.get("resolution", "") or ""
    clean_resolution, resolution_categories = redaction.redact(raw_resolution)
    if resolution_categories:
        internal_flags.append(
            f"REDACTED: {', '.join(resolution_categories)} removed from resolution"
        )

    injection_reason = detect.injection_check(raw_notes)
    if injection_reason:
        internal_flags.append(f"INJECTION_ATTEMPT: {injection_reason}")
        # spec.md §7c: structured fields only, notes excluded entirely (not screened for
        # safe fragments) — a manipulative note is not trusted for partial use either.
        parts = report.get("parts_used") or []
        text = (
            f"**{asset} — {date}**\n\n"
            f"What was done: {clean_resolution or 'Not recorded.'}\n"
            f"{_format_parts(parts)}\n"
            f"Time on site: {_format_hours(report.get('stated_duration_hours'))}.\n\n"
            f"_This report is undergoing an additional internal review before further "
            f"detail is added; the client-visible facts above are confirmed._"
        )
        return {
            "report_id": report_id,
            "status": "caveated",
            "published_text": text,
            "internal_flags": internal_flags,
        }

    clean_notes, categories = redaction.redact(raw_notes)
    if categories:
        internal_flags.append(f"REDACTED: {', '.join(categories)} removed from notes")

    insufficient_reason = detect.insufficient_data_check(report, clean_notes)
    if insufficient_reason:
        internal_flags.append(f"INSUFFICIENT_DATA: {insufficient_reason}")
        text = (
            f"**{asset} — {date}**\n\n"
            f"This report did not contain enough detail to produce a reliable summary. "
            f"Our team is following up internally and will update you if anything further "
            f"is needed."
        )
        return {
            "report_id": report_id,
            "status": "insufficient",
            "published_text": text,
            "internal_flags": internal_flags,
        }

    contradiction_reason = detect.contradiction_check(report)  # checks raw fields, by design
    parts = report.get("parts_used") or []
    recommend_sentences, other_sentences = _split_notes_by_purpose(clean_notes)
    outstanding = " ".join(recommend_sentences) if recommend_sentences else None
    found_done = _found_done_text(clean_resolution, other_sentences)

    lines = [
        f"**{asset} — {date}**",
        "",
        f"What was found / done: {found_done}",
        _format_parts(parts),
        f"Outstanding / recommended: {outstanding if outstanding else 'None noted.'}",
        f"Time on site: {_format_hours(report.get('stated_duration_hours'))}.",
    ]
    status = "published"
    if contradiction_reason:
        internal_flags.append(f"CONTRADICTION: {contradiction_reason}")
        lines.append(
            ""
            "_Note: some details in this report do not fully agree with each other "
            "internally. We are reviewing and will follow up if anything changes._"
        )
        status = "caveated"

    return {
        "report_id": report_id,
        "status": status,
        "published_text": "\n".join(lines),
        "internal_flags": internal_flags,
    }


def run_batch(input_path: Path, summaries_out: Path, audit_out: Path) -> list[dict]:
    results = []
    with input_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            report = json.loads(line)
            results.append(build_summary(report))

    summaries_out.parent.mkdir(parents=True, exist_ok=True)
    with summaries_out.open("w") as f:
        f.write("# Field Service Report Summaries — Customer Portal\n\n")
        for r in results:
            f.write(f"## {r['report_id']}\n\n{r['published_text']}\n\n---\n\n")

    audit_entries = [
        {"report_id": r["report_id"], "flags": r["internal_flags"]}
        for r in results
        if r["internal_flags"]
    ]
    audit_out.parent.mkdir(parents=True, exist_ok=True)
    with audit_out.open("w") as f:
        json.dump(audit_entries, f, indent=2)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/service_reports.jsonl", type=Path)
    parser.add_argument("--summaries-out", default="output/summaries.md", type=Path)
    parser.add_argument("--audit-out", default="output/audit_log.json", type=Path)
    args = parser.parse_args()

    results = run_batch(args.input, args.summaries_out, args.audit_out)
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"Processed {len(results)} reports -> {args.summaries_out}")
    print(f"Status breakdown: {counts}")
    flagged = sum(1 for r in results if r["internal_flags"])
    print(f"{flagged} report(s) raised an internal flag -> {args.audit_out}")


if __name__ == "__main__":
    main()
