"""Encoding tolerance and pathological-cell robustness."""

import io

from fastapi.testclient import TestClient

from app.main import app
from parsers import csv_parser

client = TestClient(app)


def _detect(name: str, raw: bytes):
    return client.post("/api/detect", files={"file": (name, io.BytesIO(raw), "text/csv")})


class TestEncodings:
    CSV = "id,name,email\n1,José Muñoz,jose@example.com\n"

    def test_utf8(self):
        assert _detect("a.csv", self.CSV.encode("utf-8")).status_code == 200

    def test_utf8_bom(self):
        assert _detect("a.csv", self.CSV.encode("utf-8-sig")).status_code == 200

    def test_utf16_excel_export(self):
        r = _detect("a.csv", self.CSV.encode("utf-16"))
        assert r.status_code == 200

    def test_latin1(self):
        r = _detect("a.csv", self.CSV.encode("latin-1"))
        assert r.status_code == 200


class TestPathologicalCells:
    def test_10k_char_cell_roundtrip(self):
        big = "x" * 10_000
        csv = f'id,name,notes\n1,John Smith,"{big}"\n'
        r = client.post("/api/anonymize", files={"file": ("a.csv", io.BytesIO(csv.encode()), "text/csv")})
        assert r.status_code == 200
        headers, rows = csv_parser.parse(r.text)
        assert rows[0][2] == big          # non-PII untouched, intact
        assert rows[0][1] != "John Smith"

    def test_quotes_commas_newlines_in_cells(self):
        csv = 'id,name,email\n1,"Smith, John ""JJ""","john@x.com"\n2,"Li\nMei",mei@y.org\n'
        r = client.post("/api/anonymize", files={"file": ("a.csv", io.BytesIO(csv.encode()), "text/csv")})
        assert r.status_code == 200
        headers, rows = csv_parser.parse(r.text)
        assert len(rows) == 2
        assert "john@x.com" not in r.text

    def test_duplicate_headers_survive(self):
        csv = "id,name,name\n1,John Smith,Mary Jones\n"
        r = client.post("/api/detect", files={"file": ("a.csv", io.BytesIO(csv.encode()), "text/csv")})
        assert r.status_code == 200
