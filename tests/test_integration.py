"""FP5 integration tests: run_tables, hashing, and multi-format API."""

import io
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from engine.mapping import MappingStore
from engine.pipeline import run_tables
from engine.techniques import get_technique
from parsers import sql_parser

client = TestClient(app)

SAMPLES = Path(__file__).parent.parent / "samples"
COMPANY_SQL = (SAMPLES / "company.sql").read_text()


def _upload(path: str, name: str, content: str, extra: dict | None = None):
    return client.post(
        path,
        files={"file": (name, io.BytesIO(content.encode()), "text/plain")},
        data=extra or {},
    )


class TestRunTables:
    def test_cross_table_consistency(self):
        tables = sql_parser.parse(COMPANY_SQL)
        out, plans, store = run_tables(tables)
        customers = next(t for t in out if t["name"] == "customers")
        orders = next(t for t in out if t["name"] == "orders")
        # John Smith (customers row 0) == customer_name in orders rows 0 and 2
        name_idx = customers["headers"].index("name")
        oname_idx = orders["headers"].index("customer_name")
        assert customers["rows"][0][name_idx] == orders["rows"][0][oname_idx]
        assert orders["rows"][0][oname_idx] == orders["rows"][2][oname_idx]
        assert customers["rows"][0][name_idx] != "John Smith"
        # plans were auto-built per table
        assert set(plans) == {"customers", "orders"}

    def test_untouched_when_plan_empty(self):
        tables = sql_parser.parse(COMPANY_SQL)
        out, _, _ = run_tables(tables, plans={"customers": [], "orders": []})
        assert out[0]["rows"] == tables[0]["rows"]


class TestHashing:
    def test_deterministic_and_keyed(self):
        t = get_technique("hashing")
        a = t.anonymize("email", "john@x.com", MappingStore(seed="k"))
        b = t.anonymize("email", "john@x.com", MappingStore(seed="k"))
        c = t.anonymize("email", "john@x.com", MappingStore(seed="other"))
        assert a == b and a != c and len(a) == 16
        assert a != "john@x.com"


class TestSqlApi:
    def test_detect_groups_by_table(self):
        r = _upload("/api/detect", "company.sql", COMPANY_SQL)
        assert r.status_code == 200
        data = r.json()
        assert data["tables"] == ["customers", "orders"]
        tables_hit = {d["table"] for d in data["detected"]}
        assert tables_hit == {"customers", "orders"}

    def test_anonymize_roundtrip_consistent(self):
        r = _upload("/api/anonymize", "company.sql", COMPANY_SQL)
        assert r.status_code == 200
        out = r.text
        assert "John Smith" not in out and "john.smith@example.com" not in out
        # non-data statements survive
        assert "DROP TABLE IF EXISTS orders" in out
        assert "UPDATE customers SET phone" in out
        # output re-parses, and cross-table consistency holds
        tables = sql_parser.parse(out)
        customers = next(t for t in tables if t["name"] == "customers")
        orders = next(t for t in tables if t["name"] == "orders")
        n = customers["rows"][0][customers["headers"].index("name")]
        assert orders["rows"][0][orders["headers"].index("customer_name")] == n

    def test_plan_override_scoped_to_table(self):
        plan = [{"table": "customers", "column": "ssn", "pii_type": "ssn", "technique": "nulling"}]
        r = _upload("/api/anonymize", "company.sql", COMPANY_SQL, {"plan_json": json.dumps(plan)})
        assert r.status_code == 200
        tables = sql_parser.parse(r.text)
        customers = next(t for t in tables if t["name"] == "customers")
        ssn_idx = customers["headers"].index("ssn")
        assert all(row[ssn_idx] == "" for row in customers["rows"])
        # orders table untouched by this plan
        orders = next(t for t in tables if t["name"] == "orders")
        assert orders["rows"][0][orders["headers"].index("customer_name")] == "John Smith"

    def test_rejects_unknown_table(self):
        plan = [{"table": "ghost", "column": "ssn", "pii_type": "ssn", "technique": "nulling"}]
        r = _upload("/api/anonymize", "company.sql", COMPANY_SQL, {"plan_json": json.dumps(plan)})
        assert r.status_code == 422


class TestTxtApi:
    TXT = "Contact John at john@x.com or 612-555-1234. Server: 10.0.0.1. Again: john@x.com"

    def test_detect_counts(self):
        r = _upload("/api/detect", "notes.txt", self.TXT)
        data = r.json()
        assert data["mode"] == "text"
        assert data["matches_by_type"]["email"] == 2

    def test_anonymize_consistent(self):
        r = _upload("/api/anonymize", "notes.txt", self.TXT)
        out = r.text
        assert "john@x.com" not in out and "612-555-1234" not in out
        # the two email occurrences map to the same replacement
        words = [w.strip(".,") for w in out.split()]
        emails = [w for w in words if "@" in w]
        assert len(emails) == 2 and emails[0] == emails[1]

    def test_txt_technique_override(self):
        r = _upload("/api/anonymize", "notes.txt", self.TXT, {"technique": "nulling"})
        assert "john@x.com" not in r.text


class TestJsonApi:
    JSON = json.dumps([
        {"id": "1", "name": "John Smith", "email": "john@x.com"},
        {"id": "2", "name": "Mary Jones", "email": "mary@y.org"},
    ])

    def test_roundtrip(self):
        r = _upload("/api/anonymize", "people.json", self.JSON)
        assert r.status_code == 200
        data = json.loads(r.text)
        assert data[0]["id"] == "1"
        assert data[0]["name"] != "John Smith"


def test_rejects_unsupported_extension():
    r = _upload("/api/detect", "x.exe", "junk")
    assert r.status_code == 400
