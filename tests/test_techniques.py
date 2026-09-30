"""Tests for Sophie's anonymization techniques."""

import pytest

from engine.mapping import MappingStore
from engine.techniques import get_technique


@pytest.fixture
def store():
    return MappingStore()


class TestPartialMasking:
    def test_name(self, store):
        technique = get_technique("partial_masking")
        assert technique.anonymize("name", "John Smith", store) == "J*** S****"

    def test_email(self, store):
        technique = get_technique("partial_masking")
        assert (
            technique.anonymize("email", "john.smith@gmail.com", store)
            == "j*********@gmail.com"
        )

    def test_phone(self, store):
        technique = get_technique("partial_masking")
        assert (
            technique.anonymize("phone", "612-555-1234", store)
            == "***-***-1234"
        )

    def test_address(self, store):
        technique = get_technique("partial_masking")
        assert (
            technique.anonymize("address", "123 Main Street", store)
            == "*** Main Street"
        )

    def test_dob_year_first(self, store):
        technique = get_technique("partial_masking")
        assert (
            technique.anonymize("dob", "1990-05-15", store)
            == "1990-**-**"
        )

    def test_dob_year_last(self, store):
        technique = get_technique("partial_masking")
        assert (
            technique.anonymize("dob", "05/15/1990", store)
            == "**/**/1990"
        )

    def test_zip(self, store):
        technique = get_technique("partial_masking")
        assert technique.anonymize("zip", "55401", store) == "554**"

    def test_ssn(self, store):
        technique = get_technique("partial_masking")
        assert (
            technique.anonymize("ssn", "123-45-6789", store)
            == "***-**-6789"
        )

    def test_ip(self, store):
        technique = get_technique("partial_masking")
        assert (
            technique.anonymize("ip", "192.168.1.25", store)
            == "***.***.***.25"
        )

    def test_card(self, store):
        technique = get_technique("partial_masking")
        assert (
            technique.anonymize("card", "4111 1111 1111 1111", store)
            == "**** **** **** 1111"
        )

    def test_empty_value(self, store):
        technique = get_technique("partial_masking")
        assert technique.anonymize("email", "", store) == ""

    def test_unknown_pii_type(self, store):
        technique = get_technique("partial_masking")
        value = "some random value"
        assert technique.anonymize("unknown", value, store) == value

    def test_malformed_dob_is_unchanged(self, store):
        technique = get_technique("partial_masking")
        value = "1990.05.15"
        assert technique.anonymize("dob", value, store) == value


class TestGeneralization:
    def test_dob_year_first(self, store):
        technique = get_technique("generalization")
        assert (
            technique.anonymize("dob", "1990-05-15", store)
            == "1990"
        )

    def test_dob_year_last(self, store):
        technique = get_technique("generalization")
        assert (
            technique.anonymize("dob", "05/15/1990", store)
            == "1990"
        )

    def test_zip(self, store):
        technique = get_technique("generalization")
        assert technique.anonymize("zip", "55401", store) == "554XX"

    def test_zip_plus_four(self, store):
        technique = get_technique("generalization")
        assert (
            technique.anonymize("zip", "55401-1234", store)
            == "554XX"
        )

    def test_short_zip_is_unchanged(self, store):
        technique = get_technique("generalization")
        assert technique.anonymize("zip", "12", store) == "12"

    def test_ip(self, store):
        technique = get_technique("generalization")
        assert (
            technique.anonymize("ip", "192.168.1.25", store)
            == "192.168.1.0"
        )

    def test_malformed_ip_is_unchanged(self, store):
        technique = get_technique("generalization")
        value = "not.an.ip"
        assert technique.anonymize("ip", value, store) == value

    def test_name(self, store):
        technique = get_technique("generalization")
        assert technique.anonymize("name", "John Smith", store) == "J. S."

    def test_email(self, store):
        technique = get_technique("generalization")
        assert (
            technique.anonymize("email", "john@gmail.com", store)
            == "gmail.com"
        )

    def test_phone(self, store):
        technique = get_technique("generalization")
        assert (
            technique.anonymize("phone", "612-555-1234", store)
            == "612-XXX-XXXX"
        )

    def test_ssn(self, store):
        technique = get_technique("generalization")
        assert (
            technique.anonymize("ssn", "123-45-6789", store)
            == "123-XX-XXXX"
        )

    def test_card(self, store):
        technique = get_technique("generalization")
        assert (
            technique.anonymize("card", "4111 1111 1111 1111", store)
            == "411111-XXXX-XXXX-XXXX"
        )

    def test_address_unchanged(self, store):
        technique = get_technique("generalization")
        value = "123 Main Street"
        assert technique.anonymize("address", value, store) == value

    def test_empty_value(self, store):
        technique = get_technique("generalization")
        assert technique.anonymize("email", "", store) == ""

    def test_unknown_pii_type(self, store):
        technique = get_technique("generalization")
        value = "some value"
        assert technique.anonymize("unknown", value, store) == value


class TestNulling:
    def test_nulling_returns_empty_string(self, store):
        technique = get_technique("nulling")
        assert technique.anonymize("name", "John Smith", store) == ""

    @pytest.mark.parametrize(
        "pii_type,value",
        [
            ("name", "John Smith"),
            ("email", "john@gmail.com"),
            ("phone", "612-555-1234"),
            ("address", "123 Main Street"),
            ("dob", "1990-05-15"),
            ("zip", "55401"),
            ("ssn", "123-45-6789"),
            ("ip", "192.168.1.25"),
            ("card", "4111 1111 1111 1111"),
        ],
    )
    def test_nulling_all_pii_types(self, store, pii_type, value):
        technique = get_technique("nulling")
        assert technique.anonymize(pii_type, value, store) == ""

    def test_nulling_empty_value(self, store):
        technique = get_technique("nulling")
        assert technique.anonymize("email", "", store) == ""


class TestTechniqueRegistry:
    def test_partial_masking_registered(self):
        assert get_technique("partial_masking").name == "partial_masking"

    def test_generalization_registered(self):
        assert get_technique("generalization").name == "generalization"

    def test_nulling_registered(self):
        assert get_technique("nulling").name == "nulling"