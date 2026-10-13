"""FastAPI application -- OWNER: CHRIS.

Endpoints:
    GET  /            -> upload UI (static)
    GET  /api/health  -> liveness check (also used to warm Render before demos)
    POST /api/detect  -> upload a file, get the detection plan as JSON
    POST /api/anonymize -> upload a file (+ optional edited plan), download result

Supported formats, dispatched by extension:
    .csv  single table            .json single table (array of objects)
    .sql  multi-table (per-table detection, shared mapping store)
    .txt  free text (pattern-detectable PII only: email/phone/ssn/ip/card)
"""

from __future__ import annotations

import io
import json
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from engine import pipeline
from engine.mapping import MappingStore
from engine.pipeline import ColumnPlan
from engine.techniques import available_techniques
from parsers import csv_parser, json_parser, sql_parser, txt_parser

app = FastAPI(title="Data Anonymizer", version="0.3.0 (FP5)")

STATIC_DIR = Path(__file__).parent / "static"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
SUPPORTED = (".csv", ".json", ".sql", ".txt")


async def _read_upload(file: UploadFile) -> tuple[str, str]:
    """Return (extension, decoded text) or raise."""
    name = (file.filename or "").lower()
    ext = next((e for e in SUPPORTED if name.endswith(e)), None)
    if ext is None:
        raise HTTPException(400, f"Unsupported file type. Supported: {', '.join(SUPPORTED)}")
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File larger than 10 MB")
    try:
        return ext, raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "File is not valid UTF-8 text")


def _parse_tabular(ext: str, text: str) -> tuple[list[str], list[list[str]]]:
    try:
        if ext == ".csv":
            return csv_parser.parse(text)
        return json_parser.parse(text)
    except ValueError as e:
        raise HTTPException(400, str(e))


def _plan_from_json(plan_json: str, valid_techniques: set[str]) -> list[ColumnPlan]:
    try:
        raw = json.loads(plan_json)
        plan = []
        for item in raw:
            if item["technique"] not in valid_techniques:
                raise HTTPException(422, f"Unknown technique: {item['technique']!r}")
            plan.append(ColumnPlan(
                item["column"], item["pii_type"], item["technique"], item.get("table", "")
            ))
        return plan
    except (json.JSONDecodeError, KeyError, TypeError):
        raise HTTPException(400, "plan_json must be a JSON list of {column, pii_type, technique[, table]}")


def _stream(text: str, filename: str, media_type: str) -> StreamingResponse:
    return StreamingResponse(
        io.BytesIO(text.encode()),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _out_name(filename: str | None, ext: str) -> str:
    base = (filename or f"data{ext}")
    stem = base[: -len(ext)] if base.lower().endswith(ext) else base
    return f"{stem}_anonymized{ext}"


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/api/health")
def health():
    return {"status": "ok", "techniques": available_techniques(), "formats": list(SUPPORTED)}


@app.post("/api/detect")
async def detect(file: UploadFile = File(...)):
    ext, text = await _read_upload(file)

    if ext in (".csv", ".json"):
        headers, rows = _parse_tabular(ext, text)
        plan = pipeline.build_plan(headers, rows)
        return {
            "filename": file.filename, "mode": "tabular", "row_count": len(rows),
            "columns": headers,
            "detected": [
                {"table": "", "column": p.header, "pii_type": p.pii_type, "technique": p.technique}
                for p in plan
            ],
        }

    if ext == ".sql":
        tables = sql_parser.parse(text)
        if not tables:
            raise HTTPException(400, "No CREATE TABLE/INSERT statements found")
        detected = []
        for t in tables:
            for p in pipeline.build_plan(t["headers"], t["rows"]):
                detected.append({
                    "table": t["name"], "column": p.header,
                    "pii_type": p.pii_type, "technique": p.technique,
                })
        return {
            "filename": file.filename, "mode": "tabular",
            "row_count": sum(len(t["rows"]) for t in tables),
            "tables": [t["name"] for t in tables],
            "detected": detected,
        }

    # .txt — free text: report match counts per PII type
    matches = txt_parser.find_matches(text)
    counts: dict[str, int] = {}
    for _, _, pii_type, _ in matches:
        counts[pii_type] = counts.get(pii_type, 0) + 1
    return {
        "filename": file.filename, "mode": "text",
        "match_count": len(matches),
        "matches_by_type": counts,
        "detected": [
            {"table": "", "column": f"(free text: {ptype})", "pii_type": ptype, "technique": "substitution"}
            for ptype in sorted(counts)
        ],
    }


@app.post("/api/anonymize")
async def anonymize(
    file: UploadFile = File(...),
    plan_json: str | None = Form(None),
    technique: str = Form("substitution"),   # used for .txt only
    seed: str = Form("team13-dev-seed"),
):
    ext, text = await _read_upload(file)
    valid = set(available_techniques())
    store = MappingStore(seed=seed)
    out_name = _out_name(file.filename, ext)

    if ext in (".csv", ".json"):
        headers, rows = _parse_tabular(ext, text)
        if plan_json:
            plan = _plan_from_json(plan_json, valid)
            for p in plan:
                if p.header not in headers:
                    raise HTTPException(422, f"Unknown column: {p.header!r}")
        else:
            plan = pipeline.build_plan(headers, rows)
        if not plan:
            raise HTTPException(422, "No PII columns detected in this file")
        result = pipeline.run(headers, rows, plan, store)
        if ext == ".csv":
            return _stream(csv_parser.serialize(result.headers, result.rows), out_name, "text/csv")
        return _stream(json_parser.serialize(result.headers, result.rows), out_name, "application/json")

    if ext == ".sql":
        tables = sql_parser.parse(text)
        if not tables:
            raise HTTPException(400, "No CREATE TABLE/INSERT statements found")
        plans: dict[str, list[ColumnPlan]] = {}
        if plan_json:
            table_headers = {t["name"]: t["headers"] for t in tables}
            for p in _plan_from_json(plan_json, valid):
                if p.table not in table_headers:
                    raise HTTPException(422, f"Unknown table: {p.table!r}")
                if p.header not in table_headers[p.table]:
                    raise HTTPException(422, f"Unknown column {p.header!r} in table {p.table!r}")
                plans.setdefault(p.table, []).append(p)
            # Tables the user's plan doesn't mention are left untouched
            for t in tables:
                plans.setdefault(t["name"], [])
        out_tables, _, _ = pipeline.run_tables(tables, store, plans or None)
        return _stream(sql_parser.serialize(text, out_tables), out_name, "application/sql")

    # .txt
    if technique not in valid:
        raise HTTPException(422, f"Unknown technique: {technique!r}")
    return _stream(txt_parser.anonymize_text(text, store, technique), out_name, "text/plain")
