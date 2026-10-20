"""Tests for the four techniques added to reach ten: format_preserving,
shuffling, perturbation, synthetic."""

from collections import Counter
from datetime import date

from engine.mapping import MappingStore
from engine.pipeline import ColumnPlan, run
from engine.techniques import available_techniques, get_technique


def _luhn_ok(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    total = 0
    for n, d in enumerate(reversed(digits)):
        if n % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def test_registry_has_ten():
    assert len(available_techniques()) == 10


class TestFormatPreserving:
    def test_card_same_shape_and_luhn_valid(self):
        t = get_technique("format_preserving")
        fake = t.anonymize("card", "4111 1111 1111 1111", MappingStore())
        assert fake != "4111 1111 1111 1111"
        assert len(fake) == 19 and fake[4] == fake[9] == fake[14] == " "
        assert _luhn_ok(fake)

    def test_phone_keeps_separators(self):
        t = get_technique("format_preserving")
        fake = t.anonymize("phone", "612-555-1234", MappingStore())
        assert len(fake) == 12 and fake[3] == fake[7] == "-"
        assert fake.replace("-", "").isdigit()

    def test_ip_valid_octets(self):
        t = get_technique("format_preserving")
        fake = t.anonymize("ip", "192.168.1.10", MappingStore())
        octets = fake.split(".")
        assert len(octets) == 4 and all(1 <= int(o) <= 254 for o in octets)

    def test_dob_is_real_date_same_format(self):
        t = get_technique("format_preserving")
        fake = t.anonymize("dob", "1988-03-16", MappingStore())
        y, m, d = fake.split("-")
        date(int(y), int(m), int(d))  # raises if invalid

    def test_deterministic_and_consistent(self):
        t = get_technique("format_preserving")
        store = MappingStore(seed="k")
        a = t.anonymize("ssn", "123-45-6789", store)
        b = t.anonymize("ssn", "123-45-6789", store)
        c = t.anonymize("ssn", "123-45-6789", MappingStore(seed="k"))
        assert a == b == c
        assert a != t.anonymize("ssn", "123-45-6789", MappingStore(seed="other"))


class TestShuffling:
    def test_same_values_different_order(self):
        headers = ["id", "name"]
        rows = [[str(i), f"Person {i}"] for i in range(20)]
        plan = [ColumnPlan("name", "name", "shuffling")]
        result = run(headers, rows, plan, MappingStore(seed="s"))
        original = [r[1] for r in rows]
        shuffled = [r[1] for r in result.rows]
        assert Counter(shuffled) == Counter(original)
        assert shuffled != original
        # ids untouched
        assert [r[0] for r in result.rows] == [r[0] for r in rows]

    def test_deterministic_per_seed(self):
        headers = ["name"]
        rows = [[f"P{i}"] for i in range(10)]
        plan = [ColumnPlan("name", "name", "shuffling")]
        r1 = run(headers, rows, plan, MappingStore(seed="s"))
        r2 = run(headers, rows, plan, MappingStore(seed="s"))
        assert r1.rows == r2.rows


class TestPerturbation:
    def test_integer_within_bounds(self):
        t = get_technique("perturbation")
        fake = t.anonymize("zip", "100000", MappingStore())
        assert fake.isdigit() and abs(int(fake) - 100000) <= 5000

    def test_decimal_keeps_precision(self):
        t = get_technique("perturbation")
        fake = t.anonymize("zip", "102543.75", MappingStore())
        assert len(fake.split(".")[1]) == 2

    def test_dob_shifts_but_stays_valid(self):
        t = get_technique("perturbation")
        fake = t.anonymize("dob", "1988-03-16", MappingStore())
        y, m, d = fake.split("-")
        shifted = date(int(y), int(m), int(d))
        assert shifted != date(1988, 3, 16)
        assert abs((shifted - date(1988, 3, 16)).days) <= 183

    def test_non_numeric_fails_closed(self):
        t = get_technique("perturbation")
        assert t.anonymize("name", "John Smith", MappingStore()) == "*" * 10

    def test_deterministic(self):
        t = get_technique("perturbation")
        assert t.anonymize("zip", "55416", MappingStore(seed="k")) == \
               t.anonymize("zip", "55416", MappingStore(seed="k"))


class TestSynthetic:
    def test_replaces_all_without_linkage(self):
        headers = ["name"]
        rows = [["John Smith"], ["Mary Jones"], ["John Smith"]]
        plan = [ColumnPlan("name", "name", "synthetic")]
        result = run(headers, rows, plan, MappingStore(seed="s"))
        values = [r[0] for r in result.rows]
        assert "John Smith" not in values
        # duplicates are NOT preserved: the two John Smith rows differ
        assert values[0] != values[2]

    def test_blanks_stay_blank(self):
        headers = ["email"]
        rows = [["a@x.com"], [""], ["b@y.com"]]
        plan = [ColumnPlan("email", "email", "synthetic")]
        result = run(headers, rows, plan, MappingStore())
        assert result.rows[1][0] == ""

    def test_deterministic_per_seed(self):
        headers = ["name"]
        rows = [["A"], ["B"]]
        plan = [ColumnPlan("name", "name", "synthetic")]
        r1 = run(headers, rows, plan, MappingStore(seed="s"))
        r2 = run(headers, rows, plan, MappingStore(seed="s"))
        assert r1.rows == r2.rows


class TestReversibleBoundary:
    def test_format_preserving_is_reversible(self):
        from engine.keyfile import REVERSIBLE_TECHNIQUES
        assert "format_preserving" in REVERSIBLE_TECHNIQUES
        assert "shuffling" not in REVERSIBLE_TECHNIQUES
        assert "synthetic" not in REVERSIBLE_TECHNIQUES
        assert "perturbation" not in REVERSIBLE_TECHNIQUES
