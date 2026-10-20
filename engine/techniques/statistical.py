"""Shuffling, perturbation, and synthetic generation -- OWNER: CHRIS.

Three techniques that trade linkability for statistical utility:

- shuffling: the column keeps exactly its original values, redistributed
  among rows (deterministic per project seed). Distributions survive; the
  link between a row and its value does not. Column-level, one-way.
- perturbation: numeric values get small deterministic noise (+/-5%);
  dates of birth shift by a consistent-per-value number of days. Exact
  values are gone, aggregates stay close. One-way. Fail-closed: a value
  that is neither numeric nor a recognizable date comes back fully masked,
  never raw.
- synthetic: the column is replaced wholesale with newly generated
  artificial values -- no mapping to the originals at all, not even
  consistency. Maximum privacy, no linkability. Column-level, one-way.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from faker import Faker

from engine.mapping import MappingStore
from engine.techniques.base import Technique, register


class Shuffling(Technique):
    name = "shuffling"
    column_level = True

    def anonymize(self, pii_type: str, value: str, store: MappingStore) -> str:
        raise NotImplementedError("shuffling operates on whole columns")

    def anonymize_column(self, pii_type: str, values: list[str], store: MappingStore) -> list[str]:
        out = list(values)
        rng = random.Random(store.value_seed(pii_type, "__shuffle__"))
        rng.shuffle(out)
        return out


def _parse_date(value: str):
    try:
        if len(value) >= 10 and value[4] in "-/" and value[7] == value[4]:
            sep = value[4]
            y, m, d = value.split(sep)
            return date(int(y), int(m), int(d)), f"%Y{sep}%m{sep}%d"
        if len(value) >= 8 and value[2:3] in ("-", "/"):
            sep = value[2]
            m, d, y = value.split(sep)
            return date(int(y), int(m), int(d)), f"%m{sep}%d{sep}%Y"
    except (ValueError, IndexError):
        pass
    return None, None


class Perturbation(Technique):
    name = "perturbation"

    def anonymize(self, pii_type: str, value: str, store: MappingStore) -> str:
        existing = store.get(pii_type, value)
        if existing is not None:
            return existing
        rng = random.Random(store.value_seed(pii_type, value))
        stripped = value.strip()

        parsed, fmt = _parse_date(stripped)
        if parsed is not None:
            shifted = parsed + timedelta(days=rng.randint(-183, 183))
            fake = shifted.strftime(fmt)
        else:
            try:
                number = float(stripped)
                factor = 1 + rng.uniform(-0.05, 0.05)
                if "." in stripped:
                    decimals = len(stripped.split(".")[1])
                    fake = f"{number * factor:.{decimals}f}"
                else:
                    fake = str(round(number * factor))
            except ValueError:
                # Fail closed: a value we can't perturb never passes through raw.
                fake = "*" * len(value)
        store.put(pii_type, value, fake)
        return fake


_PROVIDERS = {
    "name": lambda fk: fk.name(),
    "email": lambda fk: fk.email(),
    "phone": lambda fk: fk.numerify("###-###-####"),
    "address": lambda fk: fk.street_address(),
    "dob": lambda fk: fk.date_of_birth(minimum_age=18, maximum_age=90).isoformat(),
    "zip": lambda fk: fk.zipcode(),
    "ssn": lambda fk: fk.ssn(),
    "ip": lambda fk: fk.ipv4(),
    "card": lambda fk: fk.credit_card_number(),
}


class Synthetic(Technique):
    name = "synthetic"
    column_level = True

    def anonymize(self, pii_type: str, value: str, store: MappingStore) -> str:
        raise NotImplementedError("synthetic operates on whole columns")

    def anonymize_column(self, pii_type: str, values: list[str], store: MappingStore) -> list[str]:
        provider = _PROVIDERS.get(pii_type)
        if provider is None:
            return ["*" * len(v) for v in values]  # fail closed for unknown types
        fk = Faker("en_US")
        fk.seed_instance(store.value_seed(pii_type, "__synthetic__"))
        # Every cell gets an independent fresh value: duplicates in the
        # original do NOT stay linked. That absence of linkability is the
        # point of synthetic data.
        return [str(provider(fk)) if v and v.strip() else v for v in values]


register(Shuffling())
register(Perturbation())
register(Synthetic())
