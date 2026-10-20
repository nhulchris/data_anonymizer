"""Fixes for issues found in Sophie's fuzz pass: empty files, raw JSON
errors, and the product_name false positive."""

import io

from fastapi.testclient import TestClient

from app.main import app
from engine.detection import detect_column

client = TestClient(app)


def test_empty_file_clear_error():
    r = client.post("/api/detect", data={"filename": "empty.csv", "content_b64": ""})
    assert r.status_code == 400
    assert "empty" in r.json()["detail"].lower()


def test_empty_multipart_clear_error():
    r = client.post("/api/detect", files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")})
    assert r.status_code == 400
    assert "empty" in r.json()["detail"].lower()


def test_malformed_json_friendly_error():
    bad = '[{"name": "John"}\n{"name": "Mary"}]'
    r = client.post("/api/detect", files={"file": ("x.json", io.BytesIO(bad.encode()), "application/json")})
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert "valid JSON" in detail and "delimiter" not in detail


def test_product_name_not_flagged():
    assert detect_column("product_name") is None
    assert detect_column("item_name") is None
    assert detect_column("file_name") is None


def test_person_names_still_flagged():
    assert detect_column("customer_name") == "name"
    assert detect_column("name") == "name"
    assert detect_column("first_name") == "name"
    assert detect_column("username") == "name"
