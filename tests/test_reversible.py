"""FP6 reversible-mode tests: key file crypto, exact restore, API round-trips."""

import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from engine import keyfile
from engine.keyfile import KeyfileError
from engine.mapping import MappingStore
from engine.pipeline import run_tables
from engine.techniques import get_technique
from parsers import csv_parser, sql_parser

client = TestClient(app)

SAMPLES = Path(__file__).parent.parent / "samples"
COMPANY_SQL = (SAMPLES / "company.sql").read_text()


def _store_with_data() -> MappingStore:
    store = MappingStore(seed="test")
    t = get_technique("substitution")
    t.anonymize("name", "John Smith", store)
    t.anonymize("email", "john@x.com", store)
    return store


class TestKeyfile:
    def test_roundtrip(self):
        store = _store_with_data()
        kf = keyfile.create_keyfile(store, "hunter2")
        reverse = keyfile.load_reverse_map(kf, "hunter2")
        fakes = dict(store.items())
        assert reverse[fakes[("name", "John Smith")]] == "John Smith"
        assert reverse[fakes[("email", "john@x.com")]] == "john@x.com"

    def test_wrong_passphrase_rejected(self):
        kf = keyfile.create_keyfile(_store_with_data(), "hunter2")
        with pytest.raises(KeyfileError):
            keyfile.load_reverse_map(kf, "wrong")

    def test_garbage_rejected(self):
        with pytest.raises(KeyfileError):
            keyfile.load_reverse_map(b"not a key file", "x")

    def test_empty_passphrase_rejected(self):
        with pytest.raises(KeyfileError):
            keyfile.create_keyfile(_store_with_data(), "")

    def test_key_file_does_not_leak_plaintext(self):
        kf = keyfile.create_keyfile(_store_with_data(), "hunter2")
        assert b"John Smith" not in kf and b"john@x.com" not in kf


class TestExactRestore:
    def test_sql_values_restore_exactly(self):
        tables = sql_parser.parse(COMPANY_SQL)
        original_rows = {t["name"]: [list(r) for r in t["rows"]] for t in tables}
        store = MappingStore(seed="test")
        out_tables, _, _ = run_tables(tables, store)
        reverse = keyfile.load_reverse_map(
            keyfile.create_keyfile(store, "pw"), "pw"
        )
        for t in out_tables:
            assert keyfile.restore_rows(t["rows"], reverse) == original_rows[t["name"]]


SAMPLE_CSV = (
    "id,name,email\n"
    "1,John Smith,john@x.com\n"
    "2,Mary Jones,mary@y.org\n"
    "3,John Smith,john@x.com\n"
)


class TestReversibleApi:
    def _anonymize_reversible(self, name="t.csv", content=SAMPLE_CSV, extra=None):
        data = {"reversible": "true", "passphrase": "pw123"}
        data.update(extra or {})
        return client.post(
            "/api/anonymize",
            files={"file": (name, io.BytesIO(content.encode()), "text/plain")},
            data=data,
        )

    def test_csv_full_roundtrip_exact(self):
        r = self._anonymize_reversible()
        assert r.status_code == 200
        z = zipfile.ZipFile(io.BytesIO(r.content))
        names = sorted(z.namelist())
        assert names == ["t_anonymized.csv", "t_anonymized.key"]
        anon = z.read("t_anonymized.csv").decode()
        key = z.read("t_anonymized.key")
        assert "John Smith" not in anon

        r2 = client.post(
            "/api/restore",
            files={
                "file": ("t_anonymized.csv", io.BytesIO(anon.encode()), "text/csv"),
                "key_file": ("t_anonymized.key", io.BytesIO(key), "application/octet-stream"),
            },
            data={"passphrase": "pw123"},
        )
        assert r2.status_code == 200
        assert csv_parser.parse(r2.text) == csv_parser.parse(SAMPLE_CSV)

    def test_sql_full_roundtrip_exact(self):
        r = self._anonymize_reversible("company.sql", COMPANY_SQL)
        assert r.status_code == 200
        z = zipfile.ZipFile(io.BytesIO(r.content))
        anon = z.read("company_anonymized.sql").decode()
        key = z.read("company_anonymized.key")

        r2 = client.post(
            "/api/restore",
            files={
                "file": ("company_anonymized.sql", io.BytesIO(anon.encode()), "application/sql"),
                "key_file": ("k.key", io.BytesIO(key), "application/octet-stream"),
            },
            data={"passphrase": "pw123"},
        )
        assert r2.status_code == 200
        restored = sql_parser.parse(r2.text)
        original = sql_parser.parse(COMPANY_SQL)
        assert [t["rows"] for t in restored] == [t["rows"] for t in original]

    def test_wrong_passphrase_on_restore(self):
        r = self._anonymize_reversible()
        z = zipfile.ZipFile(io.BytesIO(r.content))
        anon = z.read("t_anonymized.csv").decode()
        key = z.read("t_anonymized.key")
        r2 = client.post(
            "/api/restore",
            files={
                "file": ("t_anonymized.csv", io.BytesIO(anon.encode()), "text/csv"),
                "key_file": ("k.key", io.BytesIO(key), "application/octet-stream"),
            },
            data={"passphrase": "wrong"},
        )
        assert r2.status_code == 422

    def test_non_reversible_technique_rejected(self):
        plan = [{"column": "name", "pii_type": "name", "technique": "nulling"}]
        r = self._anonymize_reversible(extra={"plan_json": json.dumps(plan)})
        assert r.status_code == 422
        assert "Not reversible" in r.json()["detail"]

    def test_reversible_requires_passphrase(self):
        r = client.post(
            "/api/anonymize",
            files={"file": ("t.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")},
            data={"reversible": "true"},
        )
        assert r.status_code == 422
