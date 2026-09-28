"""CSV parser -- OWNER: SOPHIE (reference implementation by Chris for FP3).

Parsers turn a file's text into (headers, rows) and back. JSON, SQL (port
from Assignment 2), and TXT follow the same pattern in this package.
"""

from __future__ import annotations

import csv
import io


def parse(text: str) -> tuple[list[str], list[list[str]]]:
    """Parse CSV text into (headers, rows). Raises ValueError on empty input."""
    reader = csv.reader(io.StringIO(text))
    table = [row for row in reader if row]
    if not table:
        raise ValueError("CSV file is empty")
    return table[0], table[1:]


def serialize(headers: list[str], rows: list[list[str]]) -> str:
    """Write (headers, rows) back to CSV text."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return buf.getvalue()
