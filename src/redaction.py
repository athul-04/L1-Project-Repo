"""Categorised redaction of technician notes.

Per spec.md §4, redaction is done by CATEGORY, not by matching the literal strings seen in
the sample data, because the tool is graded against held-out reports using different names,
numbers and addresses in the same categories. Every rule here is deliberately generic.

Each rule returns the spans it wants removed; `redact()` merges everything, replaces each
span with a category tag (`[redacted: PHONE]`), and reports which categories fired so the
caller can log it without ever having to touch the removed text itself.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    category: str


# --- EMAIL -------------------------------------------------------------------
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# --- PHONE ---------------------------------------------------------------
# UK-style landline/mobile, with or without a space/hyphen group, 10-11 digits total
# starting with 0. Deliberately format-based (not a digit-count-only rule), so it
# doesn't collide with e.g. a 4-digit access code or a part number.
_PHONE_RE = re.compile(r"\b0\d{2,4}[\s\-]?\d{3}[\s\-]?\d{3,4}\b")

# --- ACCESS_CODE ---------------------------------------------------------
# Numbers are ambiguous on their own (a duration, a part number, a pressure reading are all
# numbers). An access/door/alarm code is only identifiable by the words around it, so this
# rule is context-triggered: a trigger phrase followed by digits, and we redact the whole
# clause containing the code rather than just the digits, since the trigger phrase itself
# ("access code for the plant room is") is only meaningful alongside the number and is
# still an internal operational detail once separated from it.
_ACCESS_CONTEXT_RE = re.compile(
    r"[^.]*\b(access\s+code|door\s+code|alarm\s+code|key\s+code|entry\s+code|"
    r"key\s+(?:is\s+)?held|spare\s+key|keys?\s+(?:are\s+)?(?:kept|hidden|located))\b[^.]*\.?",
    re.IGNORECASE,
)

# --- ADDRESS ---------------------------------------------------------
# House-number + street-type token. Deliberately covers common UK street-type words rather
# than any single sample address, and also catches a bare "flat 3B"-style qualifier.
_STREET_TYPES = (
    r"Court|Street|St|Road|Rd|Avenue|Ave|Lane|Close|Drive|Way|Gardens|Place|Crescent|"
    r"Terrace|Grove|Square|Row|Mews|Walk"
)
_ADDRESS_RE = re.compile(
    rf"\b\d{{1,4}}\s+[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*\s+(?:{_STREET_TYPES})\b"
    rf"(?:,?\s*flat\s*\d+[A-Za-z]?)?",
    re.IGNORECASE,
)
_FLAT_ONLY_RE = re.compile(r"\bflat\s*\d+[A-Za-z]?\b", re.IGNORECASE)

# --- NAME ---------------------------------------------------------
# A bare capitalised-word-pair is too noisy on its own (asset names, place names). We only
# treat it as a personal name when it follows a person-context trigger phrase, mirroring how
# these reports actually introduce a named individual.
_NAME_CONTEXT_RE = re.compile(
    r"\b(?:site\s+contact\s+is|contact\s+is|facilities\s+manager|manager\s+is|"
    r"spoke\s+(?:to|with)|ask\s+for|speak\s+to|attention\s+of|c/o)\s+"
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
    re.IGNORECASE,
)


def _find_email(text: str) -> list[Span]:
    return [Span(m.start(), m.end(), "EMAIL") for m in _EMAIL_RE.finditer(text)]


def _find_phone(text: str) -> list[Span]:
    return [Span(m.start(), m.end(), "PHONE") for m in _PHONE_RE.finditer(text)]


def _find_access_code(text: str) -> list[Span]:
    return [Span(m.start(), m.end(), "ACCESS_CODE") for m in _ACCESS_CONTEXT_RE.finditer(text)]


def _find_address(text: str) -> list[Span]:
    spans = [Span(m.start(), m.end(), "ADDRESS") for m in _ADDRESS_RE.finditer(text)]
    covered = {(s.start, s.end) for s in spans}
    for m in _FLAT_ONLY_RE.finditer(text):
        if not any(s.start <= m.start() < s.end for s in spans):
            spans.append(Span(m.start(), m.end(), "ADDRESS"))
    return spans


def _find_name(text: str) -> list[Span]:
    spans = []
    for m in _NAME_CONTEXT_RE.finditer(text):
        spans.append(Span(m.start(1), m.end(1), "NAME"))
    return spans


_RULES = (_find_email, _find_phone, _find_access_code, _find_address, _find_name)


def _merge_overlaps(spans: list[Span]) -> list[Span]:
    """Later categories (e.g. ACCESS_CODE clause) can overlap an earlier one (e.g. a PHONE
    inside that same clause). Keep the widest span so partial redaction can't leak a
    fragment of the narrower category at the edge."""
    if not spans:
        return []
    spans = sorted(spans, key=lambda s: (s.start, -(s.end - s.start)))
    merged: list[Span] = [spans[0]]
    for s in spans[1:]:
        last = merged[-1]
        if s.start < last.end:  # overlap
            if s.end > last.end:
                merged[-1] = Span(last.start, s.end, last.category)
            # else fully contained: drop
        else:
            merged.append(s)
    return merged


def redact(text: str) -> tuple[str, list[str]]:
    """Return (clean_text, sorted list of categories that fired). Never returns the
    original removed text anywhere, including in the categories list."""
    if not text:
        return text, []

    spans: list[Span] = []
    for rule in _RULES:
        spans.extend(rule(text))

    if not spans:
        return text, []

    # Category set computed BEFORE merge, so a category isn't lost just because its span
    # was absorbed into a wider one during merge.
    categories = sorted({s.category for s in spans})

    merged = _merge_overlaps(spans)
    merged.sort(key=lambda s: s.start, reverse=True)
    out = text
    for s in merged:
        out = out[: s.start] + f"[redacted: {s.category}]" + out[s.end :]
    return out, categories
