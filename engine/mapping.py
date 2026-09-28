"""Consistency mapping store.

Design decisions (agreed 9/28):
- Mapping is keyed by (pii_type, original_value), NOT by column. The same
  value in two columns -- or two tables -- always maps to the same fake value.
- Determinism is on purpose: outputs are derived from a project seed, so the
  same input + same seed reproduces the same output on every run. A different
  seed produces a completely different (but internally consistent) output.
- The store records every original -> fake pair. That record is what the
  reversible mode (FP6) will encrypt into a key file; do not bypass it.
"""

from __future__ import annotations

import hashlib
import hmac


class MappingStore:
    def __init__(self, seed: str = "team13-dev-seed"):
        self.seed = seed
        self._forward: dict[tuple[str, str], str] = {}

    def value_seed(self, pii_type: str, original: str) -> int:
        """Stable per-value integer seed derived from the project seed.

        HMAC keyed by the project seed: without the seed, outputs are not
        predictable from the values alone (prevents dictionary attacks).
        """
        digest = hmac.new(
            self.seed.encode(), f"{pii_type}|{original}".encode(), hashlib.sha256
        ).digest()
        return int.from_bytes(digest[:8], "big")

    def get(self, pii_type: str, original: str) -> str | None:
        return self._forward.get((pii_type, original))

    def put(self, pii_type: str, original: str, fake: str) -> None:
        self._forward[(pii_type, original)] = fake

    def items(self):
        return self._forward.items()

    def __len__(self) -> int:
        return len(self._forward)
