"""Technique interface. Every anonymization technique implements this.

Contract:
- anonymize(pii_type, value, store) returns the replacement string.
- Empty/blank values pass through unchanged (handled by the pipeline).
- If a technique wants same-input-same-output consistency, it MUST go
  through the MappingStore (check store.get, generate, store.put) and use
  store.value_seed(...) to seed any randomness. Techniques that are pure
  transformations of the value itself (masking, nulling, generalization)
  don't need the store but still receive it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from engine.mapping import MappingStore


class Technique(ABC):
    #: registry key, e.g. "substitution"
    name: str = ""
    #: True if originals can be recovered from a key file (set by reversible wrappers)
    reversible: bool = False

    @abstractmethod
    def anonymize(self, pii_type: str, value: str, store: MappingStore) -> str:
        ...


_REGISTRY: dict[str, Technique] = {}


def register(technique: Technique) -> Technique:
    _REGISTRY[technique.name] = technique
    return technique


def get_technique(name: str) -> Technique:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown technique: {name!r}. Available: {sorted(_REGISTRY)}")
    return _REGISTRY[name]


def available_techniques() -> list[str]:
    return sorted(_REGISTRY)
