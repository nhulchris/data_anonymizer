"""Parser tests: JSON round-trip and edge cases."""

import pytest

from parsers.json_parser import parse, serialize


class TestJsonParser:
    def test_parse_basic(self):
        sample = '[{"name": "John Smith", "email": "john@x.com"}]'
        headers, rows = parse(sample)
        assert headers == ["name", "email"]
        assert rows == [["John Smith", "john@x.com"]]

    def test_round_trip(self):
        sample = """[
            {"name": "John Smith", "email": "john@gmail.com", "phone": "612-555-1234"},
            {"name": "Jane Doe", "email": "jane@yahoo.com", "phone": "651-555-9876"}
        ]"""

        headers, rows = parse(sample)
        output = serialize(headers, rows)

        headers2, rows2 = parse(output)

        assert headers2 == headers
        assert rows2 == rows

    def test_missing_key_becomes_empty_string(self):
        sample = """[
            {"name": "John Smith", "email": "john@gmail.com", "phone": "612-555-1234"},
            {"name": "Jane Doe", "phone": "651-555-9876"}
        ]"""

        headers, rows = parse(sample)

        assert headers == ["name", "email", "phone"]
        assert rows == [
            ["John Smith", "john@gmail.com", "612-555-1234"],
            ["Jane Doe", "", "651-555-9876"]
        ]

    def test_empty_array_raises(self):
        sample = "[]"

        with pytest.raises(ValueError, match="JSON file must contain a non-empty array of objects"):
            parse(sample)