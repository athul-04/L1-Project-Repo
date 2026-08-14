"""Structural checks over a report, independent of redaction.

Three checks, each returning a reason string or None:
  - contradiction_check   : fields disagree with each other (spec.md §6, §7a)
  - insufficient_data_check: too little content to summarise (spec.md §6, §7b)
  - injection_check       : notes attempt to instruct the tool (spec.md §5, §7c)

None of these functions look at redacted text — detection runs on the raw fields, since a
contradiction or an injection attempt is a property of what was written, not of what's safe
to publish.
"""
from __future__ import annotations

import re
from datetime import datetime

DURATION_MISMATCH_THRESHOLD_HOURS = 0.75  # 45 minutes, per spec.md §7d

_NO_PARTS_PHRASES = (
    "no parts needed",
    "no parts required",
    "no parts used",
    "not required",
    "no further parts",
    "inspection only",
)

_MIN_INFORMATIVE_WORDS = 4
_LOW_CONTENT_RESOLUTIONS = {
    "attended site.",
    "checked.",
    "see job sheet.",
    "attended site",
    "checked",
    "see job sheet",
}


def contradiction_check(report: dict) -> str | None:
    reasons = []

    resolution = (report.get("resolution") or "").lower()
    parts = report.get("parts_used") or []
    if parts and any(phrase in resolution for phrase in _NO_PARTS_PHRASES):
        reasons.append(
            f"resolution text states no parts were used/required, but parts_used lists "
            f"{len(parts)} item(s)"
        )

    try:
        arrived = datetime.fromisoformat(report["arrived_at"])
        departed = datetime.fromisoformat(report["departed_at"])
        span_hours = (departed - arrived).total_seconds() / 3600
        stated = float(report.get("stated_duration_hours", span_hours))
        if abs(span_hours - stated) > DURATION_MISMATCH_THRESHOLD_HOURS:
            reasons.append(
                f"stated duration ({stated:g}h) differs from arrival-to-departure span "
                f"({span_hours:.2f}h) by more than {DURATION_MISMATCH_THRESHOLD_HOURS:g}h"
            )
    except (KeyError, ValueError, TypeError):
        pass  # missing/malformed timestamps are the insufficient-data check's concern

    if not reasons:
        return None
    return "; ".join(reasons)


def insufficient_data_check(report: dict, redacted_notes: str) -> str | None:
    resolution = (report.get("resolution") or "").strip()
    notes = (redacted_notes or "").strip()

    resolution_low = resolution.lower() in _LOW_CONTENT_RESOLUTIONS or len(
        resolution.split()
    ) < _MIN_INFORMATIVE_WORDS
    notes_low = (not notes) or notes.lower() in {"see job sheet.", "see job sheet"} or len(
        notes.split()
    ) < 3

    if resolution_low and notes_low:
        return (
            "resolution text is minimal ('%s') and notes add no further usable detail"
            % (resolution or "<empty>")
        )
    return None


# Second-person / imperative language aimed at the tool or the publishing process itself,
# not at describing the visit. Deliberately keyed on the *addressee* ("the tool",
# "the summary", "this report", "publish") rather than on any specific verb, so a
# differently-worded attempt in the held-out set is still caught.
_INJECTION_RE = re.compile(
    r"\b(instruction\s+for\s+the\s+(?:summary\s+)?tool|do\s+not\s+(?:mention|include|"
    r"report|publish)\b.{0,40}\b(summary|report|tool)|"
    r"record\s+this\s+(?:visit|report)\s+as|"
    r"publish\s+(?:this\s+)?(?:directly|without\s+review|as\s*[- ]?is)|"
    r"omit\s+.{0,30}\bfrom\s+(?:the\s+)?(?:published\s+)?summary)\b",
    re.IGNORECASE,
)


def injection_check(raw_notes: str) -> str | None:
    if not raw_notes:
        return None
    m = _INJECTION_RE.search(raw_notes)
    if not m:
        return None
    return f"technician_notes contains text addressed to the tool/publishing process: matched pattern near {m.group(0)[:60]!r}"
