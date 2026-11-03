"""Regression for Sophie's finding: base64 as a text form field hits the
framework's 1MB field cap, limiting uploads to ~750KB raw. Base64 as a
FILE part has no such cap; the app's own 10MB limit is the real bound."""

import base64
import io

from fastapi.testclient import TestClient

from app.main import app
from parsers import csv_parser

client = TestClient(app)


def _big_csv(rows: int) -> str:
    return "\n".join(
        ["id,name,email"]
        + [f"{i},Person Number{i},user{i}@example.com" for i in range(rows)]
    )


def _as_file_part(content: str):
    b64 = base64.b64encode(content.encode()).decode()
    return {"content_file": ("content.b64", io.BytesIO(b64.encode()), "application/octet-stream")}


def test_text_field_path_still_capped_at_1mb():
    csv = _big_csv(22000)  # ~1MB raw, ~1.3MB base64
    b64 = base64.b64encode(csv.encode()).decode()
    r = client.post("/api/detect", data={"filename": "big.csv", "content_b64": b64})
    assert r.status_code == 400  # framework field cap — documented, UI no longer uses this path


def test_file_part_path_handles_multi_mb():
    csv = _big_csv(60000)  # ~2.8MB raw, well past the old ceiling
    r = client.post("/api/detect", data={"filename": "big.csv"}, files=_as_file_part(csv))
    assert r.status_code == 200
    assert r.json()["row_count"] == 60000


def test_file_part_anonymize_roundtrip():
    csv = _big_csv(30000)
    r = client.post("/api/anonymize", data={"filename": "big.csv"}, files=_as_file_part(csv))
    assert r.status_code == 200
    headers, rows = csv_parser.parse(r.text)
    assert len(rows) == 30000
    assert rows[0][1] != "Person Number0"


def test_own_10mb_cap_still_enforced():
    csv = _big_csv(230000)  # ~11MB raw
    r = client.post("/api/detect", data={"filename": "big.csv"}, files=_as_file_part(csv))
    assert r.status_code == 413


def test_large_reversible_roundtrip_no_collisions():
    """65k distinct names used to collide in Faker's pool, breaking restore
    with 'Ambiguous mapping'. Collision-aware generation fixes it."""
    import zipfile
    csv = _big_csv(65000)
    b64 = base64.b64encode(csv.encode()).decode()
    r = client.post(
        "/api/anonymize",
        data={"filename": "big.csv", "reversible": "true", "passphrase": "pw"},
        files={"content_file": ("content.b64", io.BytesIO(b64.encode()), "application/octet-stream")},
    )
    assert r.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(r.content))
    anon = z.read("big_anonymized.csv")
    key = z.read("big_anonymized.key")
    r2 = client.post(
        "/api/restore",
        data={"filename": "big_anonymized.csv", "passphrase": "pw"},
        files={
            "content_file": ("content.b64", io.BytesIO(base64.b64encode(anon)), "application/octet-stream"),
            "key_file": ("k.key", io.BytesIO(key), "application/octet-stream"),
        },
    )
    assert r2.status_code == 200
    assert "Person Number64999,user64999@example.com" in r2.text.replace("\r", "")
