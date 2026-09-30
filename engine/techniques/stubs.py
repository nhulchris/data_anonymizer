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
    """Partially hide sensitive values while preserving useful formatting."""

    name = "partial_masking"

    def anonymize(self, pii_type: str, value: str, store: MappingStore) -> str:
        if not value:
            return value

        if pii_type == "name":
            # John Smith -> J*** S****
            return " ".join(
                word[0] + "*" * (len(word) - 1) if len(word) > 1 else word
                for word in value.split()
            )

        elif pii_type == "email":
            # john.smith@gmail.com -> j**********@gmail.com
            if "@" not in value:
                return value

            local, domain = value.split("@", 1)

            if not local:
                return value

            if len(local) == 1:
                masked_local = local
            else:
                masked_local = local[0] + "*" * (len(local) - 1)

            return f"{masked_local}@{domain}"

        elif pii_type == "phone":
            # 612-555-1234 -> ***-***-1234
            return _mask_keep_last_digits(value)

        elif pii_type == "address":
            # 123 Main Street -> *** Main Street
            parts = value.split(maxsplit=1)

            if len(parts) == 1:
                return "*" * len(value)

            return "*" * len(parts[0]) + " " + parts[1]

        elif pii_type == "dob":
            return _mask_dob(value)

        elif pii_type == "zip":
            # 55401 -> 554**
            digits_seen = 0
            result = []

            for char in value:
                if char.isdigit():
                    digits_seen += 1
                    result.append(char if digits_seen <= 3 else "*")
                else:
                    result.append(char)

            return "".join(result)

        elif pii_type == "ssn":
            # 123-45-6789 -> ***-**-6789
            return _mask_keep_last_digits(value)

        elif pii_type == "ip":
            # 192.168.1.25 -> ***.***.***.25
            parts = value.split(".")

            if len(parts) != 4:
                return value

            return f"***.***.***.{parts[3]}"

        elif pii_type == "card":
            # 4111 1111 1111 1111 -> **** **** **** 1111
            return _mask_keep_last_digits(value)

        # Unknown PII type: leave unchanged.
        return value


def _mask_keep_last_digits(value: str, keep: int = 4) -> str:
    """Mask all digits except the last `keep` digits, preserving formatting."""

    digits = [char for char in value if char.isdigit()]

    if len(digits) < keep:
        return "*" * len(value)

    remaining = keep
    result = []

    for char in reversed(value):
        if char.isdigit():
            if remaining > 0:
                result.append(char)
                remaining -= 1
            else:
                result.append("*")
        else:
            result.append(char)

    return "".join(reversed(result))


def _mask_dob(value: str) -> str:
    """Mask month and day while preserving the four-digit year."""

    # YYYY-MM-DD or YYYY/MM/DD
    if len(value) >= 10 and value[4] in "-/" and value[7] == value[4]:
        year = value[:4]

        if year.isdigit():
            return year + value[4] + "**" + value[7] + "**"

    # MM-DD-YYYY or MM/DD/YYYY
    if len(value) >= 10 and value[2] in "-/" and value[5] == value[2]:
        separator = value[2]
        year = value[6:10]

        if year.isdigit():
            return "**" + separator + "**" + separator + year

    # Unknown date format: don't make an unsafe assumption.
    return value


class Generalization(Technique):
    """Reduce precision while keeping useful information."""

    name = "generalization"

    def anonymize(self, pii_type: str, value: str, store: MappingStore) -> str:
        if not value:
            return value

        if pii_type == "dob":
            # 1990-05-15 -> 1990
            # 05/15/1990 -> 1990
            return _generalize_dob(value)

        elif pii_type == "zip":
            # 55401 -> 554XX
            # 55401-1234 -> 554XX
            # Values shorter than 3 characters are left unchanged.
            if len(value) < 3:
                return value

            return value[:3] + "XX"

        elif pii_type == "ip":
            # 192.168.1.25 -> 192.168.1.0
            parts = value.split(".")

            if len(parts) != 4:
                return value

            if not all(part.isdigit() for part in parts):
                return value

            return f"{parts[0]}.{parts[1]}.{parts[2]}.0"

        elif pii_type == "name":
            # John Smith -> J. S.
            words = value.split()

            if not words:
                return value

            return " ".join(
                word[0] + "." for word in words if word
            )

        elif pii_type == "email":
            # john.smith@gmail.com -> gmail.com
            if "@" not in value:
                return value

            _, domain = value.split("@", 1)

            if not domain:
                return value

            return domain

        elif pii_type == "phone":
            # 612-555-1234 -> 612-XXX-XXXX
            digits = [char for char in value if char.isdigit()]

            if len(digits) < 10:
                return value

            area_code = "".join(digits[:3])

            return f"{area_code}-XXX-XXXX"

        elif pii_type == "ssn":
            # 123-45-6789 -> 123-XX-XXXX
            digits = [char for char in value if char.isdigit()]

            if len(digits) != 9:
                return value

            return f"{digits[0]}{digits[1]}{digits[2]}-XX-XXXX"

        elif pii_type == "card":
            # 4111 1111 1111 1111 -> 411111-XXXX-XXXX-XXXX
            digits = [char for char in value if char.isdigit()]

            if len(digits) < 12:
                return value

            return f"{''.join(digits[:6])}-XXXX-XXXX-XXXX"

        elif pii_type == "address":
            # We cannot reliably determine city/state from arbitrary
            # address text, so leave it unchanged rather than guessing.
            return value

        # Unknown PII type: leave unchanged.
        return value


def _generalize_dob(value: str) -> str:
    """Reduce a date of birth to just the year."""

    # YYYY-MM-DD or YYYY/MM/DD
    if len(value) >= 10 and value[4] in "-/" and value[7] == value[4]:
        year = value[:4]

        if year.isdigit():
            return year

    # MM-DD-YYYY or MM/DD/YYYY
    if len(value) >= 10 and value[2] in "-/" and value[5] == value[2]:
        year = value[6:10]

        if year.isdigit():
            return year

    # Unknown date format: don't make an unsafe assumption.
    return value
    

class Nulling(Technique):
    """Suppress the value entirely by replacing it with an empty string."""

    name = "nulling"

    def anonymize(self, pii_type: str, value: str, store: MappingStore) -> str:
        return ""


# Register when implemented -- uncomment as each one is completed:
register(PartialMasking())
register(Generalization())
register(Nulling())