"""Batch upload: several files, one shared mapping store."""

import base64
import io
import zipfile

from fastapi.testclient import TestClient

from app.main import app
from parsers import csv_parser

client = TestClient(app)

CSV_A = "id,name,email\n1,John Smith,john@x.com\n"
CSV_B = "order,customer_name,customer_email\n9,John Smith,john@x.com\n"


def _part(name: str, content: str):
    b64 = base64.b64encode(content.encode()).decode()
    return ("files", (name, io.BytesIO(b64.encode()), "application/octet-stream"))


def test_cross_file_consistency():
    r = client.post("/api/anonymize_batch", files=[_part("a.csv", CSV_A), _part("b.csv", CSV_B)])
    assert r.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(r.content))
    assert sorted(z.namelist()) == ["a_anonymized.csv", "b_anonymized.csv"]
    _, rows_a = csv_parser.parse(z.read("a_anonymized.csv").decode())
    _, rows_b = csv_parser.parse(z.read("b_anonymized.csv").decode())
    assert rows_a[0][1] == rows_b[0][1]      # same fake person across files
    assert rows_a[0][1] != "John Smith"


def test_batch_reversible_single_key():
    r = client.post(
        "/api/anonymize_batch",
        data={"reversible": "true", "passphrase": "pw"},
        files=[_part("a.csv", CSV_A), _part("b.csv", CSV_B)],
    )
    assert r.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(r.content))
    assert "batch.key" in z.namelist()
    # restore file A with the batch key
    anon = z.read("a_anonymized.csv")
    r2 = client.post(
        "/api/restore",
        data={"filename": "a_anonymized.csv", "passphrase": "pw"},
        files={
            "content_file": ("c.b64", io.BytesIO(base64.b64encode(anon)), "application/octet-stream"),
            "key_file": ("k.key", io.BytesIO(z.read("batch.key")), "application/octet-stream"),
        },
    )
    assert r2.status_code == 200 and "John Smith" in r2.text


def test_batch_mixed_formats():
    txt = "Call John at john@x.com please."
    r = client.post("/api/anonymize_batch", files=[_part("a.csv", CSV_A), _part("n.txt", txt)])
    assert r.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(r.content))
    out_txt = z.read("n_anonymized.txt").decode()
    _, rows_a = csv_parser.parse(z.read("a_anonymized.csv").decode())
    assert rows_a[0][2] in out_txt           # same fake email in both outputs


def test_batch_rejects_nonreversible_technique():
    r = client.post(
        "/api/anonymize_batch",
        data={"reversible": "true", "passphrase": "pw", "technique": "nulling"},
        files=[_part("a.csv", CSV_A)],
    )
    assert r.status_code == 422
