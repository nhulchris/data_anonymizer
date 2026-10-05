"""Pseudonymization technique and plan-override API tests."""

import io
import json

from fastapi.testclient import TestClient

from app.main import app
from engine.mapping import MappingStore
from engine.techniques import get_technique
from parsers import csv_parser

client = TestClient(app)


class TestPseudonymization:
    def test_consistent_within_run(self):
        t = get_technique("pseudonymization")
        store = MappingStore()
        assert t.anonymize("name", "John Smith", store) == t.anonymize("name", "John Smith", store)

    def test_token_format(self):
        t = get_technique("pseudonymization")
        store = MappingStore()
        assert t.anonymize("name", "John Smith", store).startswith("NAME_")
        assert t.anonymize("ssn", "123-45-6789", store).startswith("SSN_")

    def test_email_keeps_valid_shape(self):
        t = get_technique("pseudonymization")
        token = t.anonymize("email", "john@x.com", MappingStore())
        assert "@" in token and token.endswith("@anon.example")

    def test_deterministic_across_runs_same_seed(self):
        t = get_technique("pseudonymization")
        assert t.anonymize("name", "John Smith", MappingStore(seed="k")) == \
               t.anonymize("name", "John Smith", MappingStore(seed="k"))

    def test_seed_changes_token(self):
        t = get_technique("pseudonymization")
        assert t.anonymize("name", "John Smith", MappingStore(seed="k1")) != \
               t.anonymize("name", "John Smith", MappingStore(seed="k2"))

    def test_distinct_values_distinct_tokens(self):
        t = get_technique("pseudonymization")
        store = MappingStore()
        assert t.anonymize("name", "John Smith", store) != t.anonymize("name", "Mary Jones", store)


SAMPLE = (
    "id,name,email\n"
    "1,John Smith,john@x.com\n"
    "2,Mary Jones,mary@y.org\n"
)


class TestPlanOverrideApi:
    def _anonymize(self, plan):
        return client.post(
            "/api/anonymize",
            files={"file": ("t.csv", io.BytesIO(SAMPLE.encode()), "text/csv")},
            data={"plan_json": json.dumps(plan)} if plan is not None else {},
        )

    def test_override_technique_per_column(self):
        plan = [
            {"column": "name", "pii_type": "name", "technique": "nulling"},
            {"column": "email", "pii_type": "email", "technique": "pseudonymization"},
        ]
        r = self._anonymize(plan)
        assert r.status_code == 200
        _, rows = csv_parser.parse(r.text)
        assert rows[0][1] == ""                      # nulled
        assert rows[0][2].endswith("@anon.example")  # pseudonymized

    def test_rejects_unknown_technique(self):
        r = self._anonymize([{"column": "name", "pii_type": "name", "technique": "nope"}])
        assert r.status_code == 422

    def test_rejects_unknown_column(self):
        r = self._anonymize([{"column": "ghost", "pii_type": "name", "technique": "nulling"}])
        assert r.status_code == 422

    def test_rejects_malformed_json(self):
        r = client.post(
            "/api/anonymize",
            files={"file": ("t.csv", io.BytesIO(SAMPLE.encode()), "text/csv")},
            data={"plan_json": "not json"},
        )
        assert r.status_code == 400
