# Data Anonymizer

ICS 499 Capstone — Team 13 (Chris Nhul, Sophie Tony-Uduhirinwa)

Extends the Assignment 2 SQL anonymizer into a full application: upload a
dataset, PII columns are auto-detected, and sensitive values are replaced
using a selectable anonymization technique. One-way techniques now;
reversible anonymization (encrypted key file) lands in FP6.

## Stack

Python 3.11+ · FastAPI · Faker · pytest. Deployed on Render (free tier —
hit `/api/health` to warm it up before a demo).

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest                           # all tests should pass
uvicorn app.main:app --reload    # then open http://127.0.0.1:8000
```

Try it with `samples/customers.csv`.

## Layout

```
app/        FastAPI app + static UI        (owner: Chris; UI lead: Sophie)
engine/     detection, mapping, pipeline   (owner: Chris)
engine/techniques/  pluggable techniques   (substitution done; masking,
                                            generalization, nulling: Sophie)
parsers/    CSV done; JSON, SQL, TXT next  (owner: Sophie)
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

  ## Known limitations

- The JSON parser reads its column headers from the first record in the
  file. If a later record has a field the first record doesn't (for
  example, the first customer has no `email` but a later one does), that
  field is silently dropped rather than added as a new column. This is a
  deliberate simplification for this project's scope, not a bug — a more
  robust version would scan every record to build the full set of headers
  before converting to rows.

## Docs

- `SCOPE_PROPOSAL.md` — agreed scope (FP2)
- `FP_iteration_plan.md` — week-by-week plan (FP2, living document)
