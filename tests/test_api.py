"""API tests: CSV round-trip through the FastAPI endpoints."""

import io

from fastapi.testclient import TestClient

from app.main import app
from parsers import csv_parser

client = TestClient(app)

SAMPLE = (
    "id,name,email,phone,order_total\n"
    "1,John Smith,john@x.com,612-555-1234,19.99\n"
    "2,Mary Jones,mary@y.org,651-555-9876,5.00\n"
    "3,John Smith,john@x.com,612-555-1234,42.10\n"
)


def _upload(path: str):
    return client.post(path, files={"file": ("test.csv", io.BytesIO(SAMPLE.encode()), "text/csv")})


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert "substitution" in r.json()["techniques"]


def test_detect():
    r = _upload("/api/detect")
    assert r.status_code == 200
    data = r.json()
    assert data["row_count"] == 3
    detected = {d["column"]: d["pii_type"] for d in data["detected"]}
    assert detected == {"name": "name", "email": "email", "phone": "phone"}


def test_anonymize_roundtrip():
    r = _upload("/api/anonymize")
    assert r.status_code == 200
    headers, rows = csv_parser.parse(r.text)
    assert headers == ["id", "name", "email", "phone", "order_total"]
    assert len(rows) == 3
    # non-PII untouched
    assert [row[0] for row in rows] == ["1", "2", "3"]
    assert [row[4] for row in rows] == ["19.99", "5.00", "42.10"]
    # PII replaced
    assert rows[0][1] != "John Smith"
    assert rows[0][2] != "john@x.com"
    # consistency: row 3 has the same original person as row 1
    assert rows[0][1] == rows[2][1]
    assert rows[0][2] == rows[2][2]
    # different people differ
    assert rows[0][1] != rows[1][1]


def test_rejects_non_csv():
    r = client.post("/api/detect", files={"file": ("x.exe", io.BytesIO(b"junk"), "application/octet-stream")})
    assert r.status_code == 400


def test_rejects_empty_csv():
    r = client.post("/api/detect", files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")})
    assert r.status_code == 400
