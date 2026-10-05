"""Pseudonymization: replace PII with consistent opaque identifiers.

OWNER: CHRIS. Unlike substitution (realistic fake values), pseudonymization
replaces each distinct value with a stable, obviously-artificial token such
as NAME_a3f9c2d1. The same original always gets the same token (within and
across tables, via the shared MappingStore), and the token is derived from
the project seed, so runs are reproducible and tokens are not predictable
without the seed.
"""

from __future__ import annotations

from engine.mapping import MappingStore
from engine.techniques.base import Technique, register

_PREFIXES = {
    "name": "NAME",
    "email": "EMAIL",
    "phone": "PHONE",
    "address": "ADDR",
    "dob": "DOB",
    "zip": "ZIP",
    "ssn": "SSN",
    "ip": "IP",
    "card": "CARD",
}


class Pseudonymization(Technique):
    name = "pseudonymization"

    def anonymize(self, pii_type: str, value: str, store: MappingStore) -> str:
        existing = store.get(pii_type, value)
        if existing is not None:
            return existing
        prefix = _PREFIXES.get(pii_type, "PII")
        token_part = f"{store.value_seed(pii_type, value):016x}"[:8]
        token = f"{prefix}_{token_part}"
        # Emails keep a valid email shape so downstream parsers/apps that
        # validate formats continue to work.
        if pii_type == "email":
            token = f"user_{token_part}@anon.example"
        store.put(pii_type, value, token)
        return token


register(Pseudonymization())
