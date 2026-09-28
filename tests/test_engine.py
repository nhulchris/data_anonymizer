"""Engine tests: detection, mapping determinism, substitution consistency."""

from engine.detection import detect_column, detect_columns
from engine.mapping import MappingStore
from engine.techniques import get_technique


class TestDetection:
    def test_column_name_detection(self):
        assert detect_column("email") == "email"
        assert detect_column("Email_Add") == "email"
        assert detect_column("customer_name") == "name"
        assert detect_column("phone_number") == "phone"
        assert detect_column("SSN") == "ssn"
        assert detect_column("ip_address") == "ip"
        assert detect_column("credit_card") == "card"
        assert detect_column("date_of_birth") == "dob"
        assert detect_column("zip_code") == "zip"
        assert detect_column("order_total") is None

    def test_value_pattern_fallback(self):
        assert detect_column("contact", ["a@b.com", "c@d.org", "e@f.net"]) == "email"
        assert detect_column("field1", ["123-45-6789", "987-65-4321"]) == "ssn"
        assert detect_column("field2", ["10.0.0.1", "192.168.1.5"]) == "ip"
        assert detect_column("qty", ["3", "17", "250"]) is None

    def test_detect_columns_table(self):
        headers = ["id", "name", "email", "notes"]
        rows = [["1", "John Smith", "john@x.com", "vip"]]
        detected = detect_columns(headers, rows)
        assert detected == {"name": "name", "email": "email"}


class TestMappingStore:
    def test_value_seed_deterministic_across_instances(self):
        a = MappingStore(seed="s1")
        b = MappingStore(seed="s1")
        assert a.value_seed("email", "john@x.com") == b.value_seed("email", "john@x.com")

    def test_value_seed_changes_with_seed(self):
        a = MappingStore(seed="s1")
        b = MappingStore(seed="s2")
        assert a.value_seed("email", "john@x.com") != b.value_seed("email", "john@x.com")


class TestSubstitution:
    def test_same_value_same_fake_within_run(self):
        t = get_technique("substitution")
        store = MappingStore()
        f1 = t.anonymize("name", "John Smith", store)
        f2 = t.anonymize("name", "John Smith", store)
        assert f1 == f2

    def test_different_values_differ(self):
        t = get_technique("substitution")
        store = MappingStore()
        assert t.anonymize("name", "John Smith", store) != t.anonymize("name", "Mary Jones", store)

    def test_deterministic_across_runs_with_same_seed(self):
        t = get_technique("substitution")
        f1 = t.anonymize("email", "john@x.com", MappingStore(seed="k"))
        f2 = t.anonymize("email", "john@x.com", MappingStore(seed="k"))
        assert f1 == f2

    def test_seed_changes_output(self):
        t = get_technique("substitution")
        f1 = t.anonymize("email", "john@x.com", MappingStore(seed="k1"))
        f2 = t.anonymize("email", "john@x.com", MappingStore(seed="k2"))
        assert f1 != f2

    def test_output_not_original(self):
        t = get_technique("substitution")
        store = MappingStore()
        for pii_type, value in [
            ("name", "John Smith"), ("email", "john@x.com"), ("ssn", "123-45-6789"),
            ("phone", "612-555-1234"), ("ip", "10.0.0.1"), ("card", "4111111111111111"),
        ]:
            assert t.anonymize(pii_type, value, store) != value
