"""JSON parser -- OWNER: SOPHIE.

Expects a JSON array of objects, e.g.
[{"name": "John", "email": "john@x.com"}, {"name": "Jane", "email": "jane@x.com"}]
"""

from __future__ import annotations

import json


def parse(text: str) -> tuple[list[str], list[list[str]]]:
    """Parse JSON text into (headers, rows)."""
    data = json.loads(text)

    if not isinstance(data, list) or not data:
        raise ValueError("JSON file must contain a non-empty array of objects")

    headers = list(data[0].keys())

    rows = []
    for obj in data:
        row = [str(obj.get(header, "")) for header in headers]
        rows.append(row)

    return headers, rows


def serialize(headers: list[str], rows: list[list[str]]) -> str:
    """Write (headers, rows) back to JSON text."""
    records = []

    for row in rows:
        record = dict(zip(headers, row))
        records.append(record)

    return json.dumps(records, indent=2)