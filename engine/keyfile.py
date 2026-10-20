"""Reversible anonymization key file -- OWNER: CHRIS.

When reversible mode is on, the MappingStore's original->fake pairs are
exported into an encrypted key file. Restoring = decrypting the key file
and mapping fakes back to originals in the anonymized file.

Format: b"DAKF1" magic + 16-byte random salt + Fernet token.
The Fernet key is derived from the user's passphrase with PBKDF2-HMAC-SHA256
(480k iterations). Without the passphrase AND the key file, originals are
not recoverable.

Only store-backed techniques are reversible: nulling, masking, and
generalization destroy information (two different values can collapse to
the same output), so they cannot be reversed and are rejected in
reversible mode.
"""

from __future__ import annotations

import base64
import json
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from engine.mapping import MappingStore

MAGIC = b"DAKF1"
REVERSIBLE_TECHNIQUES = {"substitution", "pseudonymization", "hashing", "format_preserving"}
_ITERATIONS = 480_000


class KeyfileError(ValueError):
    """Bad passphrase or corrupted/invalid key file."""


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=_ITERATIONS)
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))


def create_keyfile(store: MappingStore, passphrase: str) -> bytes:
    """Encrypt the store's mapping into key-file bytes."""
    if not passphrase:
        raise KeyfileError("A passphrase is required for reversible mode")
    payload = json.dumps({
        "version": 1,
        "mappings": [[t, original, fake] for (t, original), fake in store.items()],
    }).encode()
    salt = os.urandom(16)
    token = Fernet(_derive_key(passphrase, salt)).encrypt(payload)
    return MAGIC + salt + token


def load_reverse_map(data: bytes, passphrase: str) -> dict[str, str]:
    """Decrypt a key file and return {fake: original}.

    Raises KeyfileError on a wrong passphrase or malformed file, and on the
    (theoretical) case of two different originals sharing one fake.
    """
    if not data.startswith(MAGIC) or len(data) < len(MAGIC) + 17:
        raise KeyfileError("Not a valid key file")
    salt = data[len(MAGIC):len(MAGIC) + 16]
    token = data[len(MAGIC) + 16:]
    try:
        payload = Fernet(_derive_key(passphrase, salt)).decrypt(token)
    except InvalidToken:
        raise KeyfileError("Wrong passphrase, or the key file is corrupted")
    mappings = json.loads(payload)["mappings"]
    reverse: dict[str, str] = {}
    for _pii_type, original, fake in mappings:
        if fake in reverse and reverse[fake] != original:
            raise KeyfileError(f"Ambiguous mapping for value {fake!r}")
        reverse[fake] = original
    return reverse


def restore_rows(rows: list[list[str]], reverse: dict[str, str]) -> list[list[str]]:
    """Map fake cell values back to originals; non-mapped cells unchanged."""
    return [[reverse.get(cell, cell) for cell in row] for row in rows]


def restore_text(text: str, reverse: dict[str, str]) -> str:
    """Restore free text by replacing fakes with originals, longest first
    (so a fake that contains another fake as a substring can't corrupt it)."""
    for fake in sorted(reverse, key=len, reverse=True):
        text = text.replace(fake, reverse[fake])
    return text
