"""FastAPI application -- OWNER: CHRIS.

Endpoints:
    GET  /            -> upload UI (static)
    GET  /api/health  -> liveness check (also used to warm Render before demos)
    POST /api/detect  -> upload a CSV, get the detection plan as JSON
    POST /api/anonymize -> upload a CSV, download the anonymized CSV
"""

from __future__ import annotations

import io
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from engine import pipeline
from engine.mapping import MappingStore
from engine.techniques import available_techniques
from parsers import csv_parser

app = FastAPI(title="Data Anonymizer", version="0.1.0 (FP3)")

STATIC_DIR = Path(__file__).parent / "static"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB for now


async def _read_csv_upload(file: UploadFile) -> tuple[list[str], list[list[str]]]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only .csv files are supported in this iteration")
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File larger than 10 MB")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "File is not valid UTF-8 text")
    try:
        return csv_parser.parse(text)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "techniques": available_techniques()}


@app.post("/api/detect")
async def detect(file: UploadFile = File(...)):
    headers, rows = await _read_csv_upload(file)
    plan = pipeline.build_plan(headers, rows)
    return {
        "filename": file.filename,
        "columns": headers,
        "row_count": len(rows),
        "detected": [
            {"column": p.header, "pii_type": p.pii_type, "technique": p.technique}
            for p in plan
        ],
    }


@app.post("/api/anonymize")
async def anonymize(file: UploadFile = File(...), seed: str = "team13-dev-seed"):
    headers, rows = await _read_csv_upload(file)
    plan = pipeline.build_plan(headers, rows)
    if not plan:
        raise HTTPException(422, "No PII columns detected in this file")
    result = pipeline.run(headers, rows, plan, MappingStore(seed=seed))
    out = csv_parser.serialize(result.headers, result.rows)
    name = (file.filename or "data.csv").rsplit(".", 1)[0] + "_anonymized.csv"
    return StreamingResponse(
        io.BytesIO(out.encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
