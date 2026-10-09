"""TXT parser -- OWNER: SOPHIE.

Scope (per team rubric): TXT support is limited to pattern-detectable PII
-- email, phone, SSN, IP, card -- found anywhere in free text. Detecting
names and addresses in free text would require NLP and is a stretch goal,
not implemented here.

Unlike csv_parser/json_parser/sql_parser, TXT has no headers/rows
structure, so this module works directly on the text: find matches, replace
them through a Technique + MappingStore, return the modified text.
"""

from __future__ import annotations

import re

from engine.mapping import MappingStore
from engine.techniques import get_technique

# Checked in this order: most specific pattern first, so e.g. a 16-digit
# card number is caught as "card" before the phone pattern could grab part
# of it. SSN and card are checked before phone for the same reason.
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("card", re.compile(r"\b(?:\d{4}[-\s]){3}\d{4}\b")),
    ("ip", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("phone", re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
]


def find_matches(text: str) -> list[tuple[int, int, str, str]]:
    """Find every PII match in text. Returns a list of
    (start, end, pii_type, matched_text), sorted by position, with
    overlapping matches resolved in PATTERNS order (earlier type wins)."""

    taken: list[tuple[int, int]] = []
    matches: list[tuple[int, int, str, str]] = []

    for pii_type, pattern in PATTERNS:
        for m in pattern.finditer(text):
            start, end = m.start(), m.end()
            overlaps = any(start < t_end and end > t_start for t_start, t_end in taken)
            if overlaps:
                continue
            taken.append((start, end))
            matches.append((start, end, pii_type, m.group(0)))

    matches.sort(key=lambda m: m[0])
    return matches


def anonymize_text(text: str, store: MappingStore, technique_name: str = "substitution") -> str:
    """Replace every pattern-detectable PII match in text using the given
    technique, keeping everything else unchanged. Same value -> same
    replacement, via the shared MappingStore (consistent with CSV/JSON/SQL)."""

    technique = get_technique(technique_name)
    matches = find_matches(text)

    result = []
    cursor = 0
    for start, end, pii_type, value in matches:
        result.append(text[cursor:start])
        result.append(technique.anonymize(pii_type, value, store))
        cursor = end
    result.append(text[cursor:])

    return "".join(result)


def parse(text: str) -> str:
    """TXT has no tabular structure -- parse() just returns the raw text.
    Kept for interface consistency with the other parsers."""
    return text


def serialize(
    text: str,
    store: MappingStore | None = None,
    technique_name: str = "substitution",
) -> str:
    """Anonymize a TXT file's pattern-detectable PII and return the result."""
    store = store if store is not None else MappingStore()
    return anonymize_text(text, store, technique_name)