"""PII detection: column-name keywords first, value-pattern fallback.

The nine supported PII types (agreed 9/28):
    name, email, phone, address, dob, zip, ssn, ip, card
"""

from __future__ import annotations

import re

PII_TYPES = ["name", "email", "phone", "address", "dob", "zip", "ssn", "ip", "card"]

# Column-name keywords. Matched case-insensitively against the normalized
# header (letters/digits only), longest keyword wins.
COLUMN_KEYWORDS: dict[str, list[str]] = {
    "email": ["email", "emailadd", "emailaddress", "mail"],
    "phone": ["phone", "phonenumber", "mobile", "cell", "telephone", "tel"],
    "ssn": ["ssn", "socialsecurity", "socialsecuritynumber", "nationalid"],
    "card": ["card", "cardnumber", "creditcard", "debitcard", "ccnum", "pan"],
    "ip": ["ip", "ipaddress", "ipaddr"],
    "dob": ["dob", "dateofbirth", "birthdate", "birthday", "born"],
    "zip": ["zip", "zipcode", "postal", "postalcode", "postcode"],
    "address": ["address", "street", "streetaddress", "addr", "homeaddress", "city"],
    "name": [
        "name", "firstname", "lastname", "fullname", "fname", "lname",
        "surname", "givenname", "middlename", "customername", "username",
    ],
}

# Value patterns (fallback when the column name is uninformative, and the
# only detection available for free text / TXT input).
VALUE_PATTERNS: dict[str, re.Pattern] = {
    "email": re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$"),
    "ssn": re.compile(r"^\d{3}-\d{2}-\d{4}$"),
    "phone": re.compile(r"^\+?1?[-. (]*\d{3}[-. )]*\d{3}[-. ]*\d{4}$"),
    "ip": re.compile(r"^(\d{1,3}\.){3}\d{1,3}$"),
    "card": re.compile(r"^(?:\d[ -]?){13,19}$"),
    "zip": re.compile(r"^\d{5}(-\d{4})?$"),
    "dob": re.compile(r"^\d{4}-\d{2}-\d{2}$|^\d{1,2}/\d{1,2}/\d{2,4}$"),
}


def _normalize(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", header.lower())


def detect_column(header: str, sample_values: list[str] | None = None) -> str | None:
    """Return the detected PII type for a column, or None.

    Column-name match wins; otherwise, if >=60% of non-empty sample values
    match a single value pattern, that type is returned.
    """
    norm = _normalize(header)
    best: tuple[int, str] | None = None
    for pii_type, keywords in COLUMN_KEYWORDS.items():
        for kw in keywords:
            if kw == norm or norm.endswith(kw) or norm.startswith(kw):
                if best is None or len(kw) > best[0]:
                    best = (len(kw), pii_type)
    if best:
        return best[1]

    if sample_values:
        values = [v.strip() for v in sample_values if v and v.strip()]
        if values:
            for pii_type, pattern in VALUE_PATTERNS.items():
                hits = sum(1 for v in values if pattern.match(v))
                if hits / len(values) >= 0.6:
                    return pii_type
    return None


def detect_columns(headers: list[str], rows: list[list[str]], sample_size: int = 20) -> dict[str, str]:
    """Map header -> detected PII type for all detected columns."""
    result: dict[str, str] = {}
    for i, header in enumerate(headers):
        samples = [row[i] for row in rows[:sample_size] if i < len(row)]
        detected = detect_column(header, samples)
        if detected:
            result[header] = detected
    return result
