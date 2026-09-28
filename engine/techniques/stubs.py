"""Technique stubs -- OWNER: SOPHIE.

Implement each against the Technique contract in base.py. Substitution
(substitution.py) is the worked example: follow its shape. Masking,
generalization, and nulling are pure transformations of the value, so they
don't need the MappingStore -- but keep the parameter, the pipeline passes it.

When one is done: implement anonymize(), remove the NotImplementedError,
add tests in tests/test_techniques.py, and it appears in the UI dropdown
automatically via the registry.
"""

from __future__ import annotations

from engine.mapping import MappingStore
from engine.techniques.base import Technique, register


class PartialMasking(Technique):
    """j***@gmail.com, ***-***-1234, **** **** **** 1111 style masking."""

    name = "partial_masking"

    def anonymize(self, pii_type: str, value: str, store: MappingStore) -> str:
        raise NotImplementedError("TODO(Sophie): implement partial masking per PII type")


class Generalization(Technique):
    """Reduce precision: DOB -> year, ZIP -> first 3 digits + 'XX', etc."""

    name = "generalization"

    def anonymize(self, pii_type: str, value: str, store: MappingStore) -> str:
        raise NotImplementedError("TODO(Sophie): implement generalization per PII type")


class Nulling(Technique):
    """Suppress the value entirely (empty string or a fixed token)."""

    name = "nulling"

    def anonymize(self, pii_type: str, value: str, store: MappingStore) -> str:
        raise NotImplementedError("TODO(Sophie): implement nulling/suppression")


# Register when implemented -- uncomment as each one is completed:
# register(PartialMasking())
# register(Generalization())
# register(Nulling())
