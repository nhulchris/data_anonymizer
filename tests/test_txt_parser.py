import pytest

from parsers.txt_parser import find_matches, anonymize_text, parse, serialize
from engine.mapping import MappingStore


# ---------------------------------------------------------
# find_matches()
# ---------------------------------------------------------

def test_find_matches_email():
    text = "Contact John at john.smith@example.com for details."
    matches = find_matches(text)
    assert len(matches) == 1
    assert matches[0][2] == "email"
    assert matches[0][3] == "john.smith@example.com"


def test_find_matches_phone():
    text = "Call me at 612-555-1234 tomorrow."
    matches = find_matches(text)
    assert len(matches) == 1
    assert matches[0][2] == "phone"
    assert matches[0][3] == "612-555-1234"


def test_find_matches_ssn():
    text = "SSN on file: 123-45-6789."
    matches = find_matches(text)
    assert len(matches) == 1
    assert matches[0][2] == "ssn"


def test_find_matches_ip():
    text = "The server IP is 192.168.1.25 as of today."
    matches = find_matches(text)
    assert len(matches) == 1
    assert matches[0][2] == "ip"


def test_find_matches_card():
    text = "Card number: 4111-1111-1111-1111 on the account."
    matches = find_matches(text)
    assert len(matches) == 1
    assert matches[0][2] == "card"


def test_find_matches_multiple_types():
    text = "Email john@example.com or call 612-555-1234."
    matches = find_matches(text)
    types = [m[2] for m in matches]
    assert "email" in types
    assert "phone" in types
    assert len(matches) == 2


def test_find_matches_no_pii():
    text = "This is a plain sentence with no sensitive data in it."
    matches = find_matches(text)
    assert matches == []


def test_find_matches_ssn_not_double_matched_as_phone():
    # An SSN-shaped number shouldn't also register as a phone match.
    text = "SSN: 123-45-6789."
    matches = find_matches(text)
    assert len(matches) == 1
    assert matches[0][2] == "ssn"


# ---------------------------------------------------------
# anonymize_text()
# ---------------------------------------------------------

def test_anonymize_text_replaces_email():
    text = "Contact john.smith@example.com for help."
    store = MappingStore()
    result = anonymize_text(text, store)
    assert "john.smith@example.com" not in result
    assert "Contact" in result
    assert "for help." in result


def test_anonymize_text_consistent_within_text():
    text = "Email john@example.com. Also reach john@example.com again."
    store = MappingStore()
    result = anonymize_text(text, store)

    # Both occurrences of the same email should be replaced with the
    # same fake value.
    first = result.split("Email ")[1].split(".")[0]
    assert result.count(first) == 2


def test_anonymize_text_leaves_non_pii_unchanged():
    text = "The weather today is sunny with a high of 75 degrees."
    store = MappingStore()
    result = anonymize_text(text, store)
    assert result == text


def test_anonymize_text_preserves_surrounding_text():
    text = "Please email jane.doe@example.com before Friday."
    store = MappingStore()
    result = anonymize_text(text, store)
    assert result.startswith("Please email ")
    assert result.endswith(" before Friday.")


def test_anonymize_text_deterministic_with_same_seed():
    text = "Reach me at john@example.com."
    result1 = anonymize_text(text, MappingStore(seed="k"))
    result2 = anonymize_text(text, MappingStore(seed="k"))
    assert result1 == result2


# ---------------------------------------------------------
# parse() / serialize()
# ---------------------------------------------------------

def test_parse_returns_raw_text():
    text = "Just some plain text with john@example.com in it."
    assert parse(text) == text


def test_serialize_anonymizes_and_returns_string():
    text = "Contact john@example.com or call 612-555-1234."
    result = serialize(text)
    assert "john@example.com" not in result
    assert "612-555-1234" not in result
    assert isinstance(result, str)


def test_serialize_shared_store_keeps_cross_call_consistency():
    store = MappingStore()
    text1 = "Email john@example.com for info."
    text2 = "Also reach john@example.com on weekends."

    result1 = serialize(text1, store=store)
    result2 = serialize(text2, store=store)

    fake1 = result1.split("Email ")[1].split(" for")[0]
    fake2 = result2.split("Also reach ")[1].split(" on")[0]
    assert fake1 == fake2