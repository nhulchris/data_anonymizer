# Data Anonymizer

ICS 499 Capstone — Team 13 (Chris Nhul, Sophie Tony-Uduhirinwa)

Extends the Assignment 2 SQL anonymizer into a full application: upload a
dataset, PII columns are auto-detected, and sensitive values are replaced
using a selectable anonymization technique per column. One-way techniques
now; reversible anonymization (encrypted key file) lands in FP6.

**Live app:** https://data-anonymizer-g90k.onrender.com (free tier — hit
`/api/health` first to wake it before a demo)

## Stack

Python 3.10+ · FastAPI · Faker · pytest. Deployed on Render, auto-deploy
from `main`.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest                           # all tests should pass
uvicorn app.main:app --reload    # then open http://127.0.0.1:8000
```

Try it with `samples/customers.csv`.

## Status

| Area | Done | Next |
|---|---|---|
| Techniques | substitution, pseudonymization, nulling, partial masking, generalization | hashing, format-preserving masking, reversible mode |
| Parsers | CSV, JSON; SQL core functions (table-level) | SQL multi-table assembly, TXT |
| App | upload → detect → per-column technique selection → download | multi-table SQL support in API/UI |

## Layout

```
app/        FastAPI app + static UI        (owner: Chris; UI lead: Sophie)
engine/     detection, mapping, pipeline   (owner: Chris)
<<<<<<< HEAD
engine/techniques/  pluggable techniques   (substitution done; masking,
                                            generalization, nulling: Sophie)
parsers/    CSV, JSON, SQL done; TXT next  (owner: Sophie)
=======
engine/techniques/  pluggable techniques   (substitution, pseudonymization:
                                            Chris; masking, generalization,
                                            nulling: Sophie)
parsers/    CSV, JSON done; SQL in progress, TXT next  (owner: Sophie)
>>>>>>> 4d84d365ab8f8cc80b7af9fb81fde1f70dd4d491
tests/      pytest suite                   (shared)
samples/    demo datasets
```

## Design decisions

- Consistency mapping is keyed by (PII type, original value) — the same
  value maps to the same fake within and across tables.
- Determinism is seeded: same input + same project seed reproduces the same
  output across runs (HMAC-derived per-value seeds; no dictionary attacks).
- Detection is column-name-first with a value-pattern fallback; 9 PII types:
  name, email, phone, address, dob, zip, ssn, ip, card.
- When the user edits the detection plan, the edited plan is authoritative:
  columns removed from it are left untouched.

## Known limitations

- The JSON parser reads its column headers from the first record in the
  file. If a later record has a field the first record doesn't, that field
  is silently dropped rather than added as a new column. This is a
  deliberate simplification for this project's scope — a more robust
  version would scan every record to build the full header set first.
- Generalization leaves street addresses unchanged (no reliable city/state
  extraction from arbitrary address text); choose substitution, nulling, or
  partial masking for address columns.

## Docs

- `SCOPE_PROPOSAL.md` — agreed scope (FP2)
- `FP_iteration_plan.md` — week-by-week plan (FP2, living document)
