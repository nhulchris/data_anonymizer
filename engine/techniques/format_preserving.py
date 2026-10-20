"""Format-preserving masking -- OWNER: CHRIS.

Replaces a value with a different value of exactly the same shape: digits
become other digits, letters become other letters (case kept), separators
and punctuation stay where they are. Downstream systems that validate
formats keep working. Extra rules per type:
- card: the replacement passes the Luhn check-digit test, like a real PAN.
- ip:   each octet lands in 1..254, so the result is a plausible address.
- dob:  the replacement is a real calendar date in the same format.

Store-backed (same original -> same replacement, reversible via key file).
"""

from __future__ import annotations

import random
import string

from engine.mapping import MappingStore
from engine.techniques.base import Technique, register


def _luhn_fix(formatted: str) -> str:
    """Adjust the last digit of a formatted card number so Luhn passes."""
    digit_positions = [i for i, ch in enumerate(formatted) if ch.isdigit()]
    if len(digit_positions) < 2:
        return formatted
    digits = [int(formatted[i]) for i in digit_positions]
    # Luhn over all but the check digit (last), doubling every second from the right
    total = 0
    for n, d in enumerate(reversed(digits[:-1])):
        if n % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    check = (10 - total % 10) % 10
    out = list(formatted)
    out[digit_positions[-1]] = str(check)
    return "".join(out)


def _same_shape(value: str, rng: random.Random) -> str:
    out = []
    for ch in value:
        if ch.isdigit():
            out.append(str(rng.randint(0, 9)))
        elif ch.isalpha():
            pool = string.ascii_uppercase if ch.isupper() else string.ascii_lowercase
            out.append(rng.choice(pool))
        else:
            out.append(ch)
    return "".join(out)


def _fake_ip(value: str, rng: random.Random) -> str:
    parts = value.split(".")
    if len(parts) != 4:
        return _same_shape(value, rng)
    return ".".join(str(rng.randint(1, 254)) for _ in parts)


def _fake_date(value: str, rng: random.Random) -> str:
    year = rng.randint(1940, 2005)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    if len(value) >= 10 and value[4] in "-/" and value[7] == value[4]:
        sep = value[4]
        return f"{year:04d}{sep}{month:02d}{sep}{day:02d}"
    if len(value) >= 8 and value[2:3] in ("-", "/") :
        sep = value[2]
        return f"{month:02d}{sep}{day:02d}{sep}{year:04d}"
    return _same_shape(value, rng)


class FormatPreserving(Technique):
    name = "format_preserving"

    def anonymize(self, pii_type: str, value: str, store: MappingStore) -> str:
        existing = store.get(pii_type, value)
        if existing is not None:
            return existing
        rng = random.Random(store.value_seed(pii_type, value))
        if pii_type == "ip":
            fake = _fake_ip(value, rng)
        elif pii_type == "dob":
            fake = _fake_date(value, rng)
        else:
            fake = _same_shape(value, rng)
            if pii_type == "card":
                fake = _luhn_fix(fake)
        store.put(pii_type, value, fake)
        return fake


register(FormatPreserving())
