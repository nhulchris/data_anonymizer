"""Anonymization pipeline: detection + technique application over tabular data."""

from __future__ import annotations

from dataclasses import dataclass, field

from engine.detection import detect_columns
from engine.mapping import MappingStore
from engine.techniques import get_technique


@dataclass
class ColumnPlan:
    header: str
    pii_type: str
    technique: str  # registry name, e.g. "substitution"
    table: str = ""  # table name for multi-table (SQL) sources; "" otherwise


@dataclass
class Result:
    headers: list[str]
    rows: list[list[str]]
    plan: list[ColumnPlan]
    values_mapped: int = 0
    notes: list[str] = field(default_factory=list)


def build_plan(headers: list[str], rows: list[list[str]], default_technique: str = "substitution") -> list[ColumnPlan]:
    """Auto-detect PII columns and propose a technique per column."""
    detected = detect_columns(headers, rows)
    return [ColumnPlan(h, t, default_technique) for h, t in detected.items()]


def run(
    headers: list[str],
    rows: list[list[str]],
    plan: list[ColumnPlan],
    store: MappingStore | None = None,
) -> Result:
    """Apply the plan to the rows. Blank values pass through unchanged."""
    store = store if store is not None else MappingStore()
    by_index = {
        headers.index(p.header): p for p in plan if p.header in headers
    }
    out_rows: list[list[str]] = []
    for row in rows:
        new_row = list(row)
        for idx, p in by_index.items():
            if idx < len(new_row) and new_row[idx] and new_row[idx].strip():
                technique = get_technique(p.technique)
                new_row[idx] = technique.anonymize(p.pii_type, new_row[idx], store)
        out_rows.append(new_row)
    return Result(headers=headers, rows=out_rows, plan=plan, values_mapped=len(store))


def run_tables(
    tables: list[dict],
    store: MappingStore | None = None,
    plans: dict[str, list[ColumnPlan]] | None = None,
    default_technique: str = "substitution",
) -> tuple[list[dict], dict[str, list[ColumnPlan]], MappingStore]:
    """Anonymize a multi-table source (e.g. a parsed SQL file).

    tables: [{"name", "headers", "rows"}, ...] as sql_parser.parse returns.
    plans: optional {table_name: [ColumnPlan, ...]} overrides; tables not in
    it get auto-detection with default_technique.

    One shared MappingStore across all tables is what gives cross-table
    consistency: the same value in two tables maps to the same fake.
    Returns (anonymized tables in the same shape, the plans used, the store).
    """
    store = store if store is not None else MappingStore()
    plans = plans or {}
    out_tables: list[dict] = []
    used_plans: dict[str, list[ColumnPlan]] = {}
    for table in tables:
        name = table["name"]
        plan = plans.get(name)
        if plan is None:
            plan = build_plan(table["headers"], table["rows"], default_technique)
            for p in plan:
                p.table = name
        result = run(table["headers"], table["rows"], plan, store)
        out_tables.append({"name": name, "headers": result.headers, "rows": result.rows})
        used_plans[name] = plan
    return out_tables, used_plans, store
