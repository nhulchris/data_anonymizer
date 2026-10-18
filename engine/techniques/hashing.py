"""Hashing: replace PII with a keyed one-way hash.

OWNER: CHRIS. HMAC-SHA256 keyed by the project seed, truncated to 16 hex
characters. One-way by design (no realistic fake, no reversal), but still
deterministic: the same value with the same seed always hashes the same,
so joins and duplicate detection keep working. Keying with the seed
prevents dictionary attacks on common values.
"""

from __future__ import annotations

import hashlib
import hmac

from engine.mapping import MappingStore
from engine.techniques.base import Technique, register


class Hashing(Technique):
    name = "hashing"

    def anonymize(self, pii_type: str, value: str, store: MappingStore) -> str:
        existing = store.get(pii_type, value)
        if existing is not None:
            return existing
        digest = hmac.new(
            store.seed.encode(), f"{pii_type}|{value}".encode(), hashlib.sha256
        ).hexdigest()[:16]
        store.put(pii_type, value, digest)
        return digest


register(Hashing())
