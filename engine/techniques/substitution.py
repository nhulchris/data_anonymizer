"""Substitution: replace PII with realistic Faker-generated values.

REFERENCE IMPLEMENTATION (Chris) -- demonstrates the Technique contract and
seeded determinism for the FP3 demo. Sophie owns this module going forward:
extend providers, locales, and edge cases as needed.
"""

from __future__ import annotations

from faker import Faker

from engine.mapping import MappingStore
from engine.techniques.base import Technique, register

_faker = Faker("en_US")

# pii_type -> generator using the module Faker instance
_PROVIDERS = {
    "name": lambda: _faker.name(),
    "email": lambda: _faker.email(),
    "phone": lambda: _faker.numerify("###-###-####"),
    "address": lambda: _faker.street_address(),
    "dob": lambda: _faker.date_of_birth(minimum_age=18, maximum_age=90).isoformat(),
    "zip": lambda: _faker.zipcode(),
    "ssn": lambda: _faker.ssn(),
    "ip": lambda: _faker.ipv4(),
    "card": lambda: _faker.credit_card_number(),
}


class Substitution(Technique):
    name = "substitution"

    def anonymize(self, pii_type: str, value: str, store: MappingStore) -> str:
        existing = store.get(pii_type, value)
        if existing is not None:
            return existing
        provider = _PROVIDERS.get(pii_type)
        if provider is None:
            return value  # unknown type: leave unchanged
        # Deterministic per (seed, pii_type, value): same input + same project
        # seed reproduces the same fake on every run, independent of row order.
        # On collision (two originals drawing the same fake -- likely at tens
        # of thousands of distinct values), retry with a salted seed until
        # unique, still deterministically.
        for attempt in range(10000):
            salt = value if attempt == 0 else f"{value}|retry{attempt}"
            _faker.seed_instance(store.value_seed(pii_type, salt))
            fake = str(provider())
            if not store.fake_taken(pii_type, fake):
                break
        else:
            # Pool exhausted (distinct values approach Faker's pool size):
            # force uniqueness with a deterministic suffix rather than ever
            # reusing a fake, which would break reversibility.
            n = 2
            base = fake
            while store.fake_taken(pii_type, fake):
                fake = f"{base} {n}"
                n += 1
        store.put(pii_type, value, fake)
        return fake


register(Substitution())
