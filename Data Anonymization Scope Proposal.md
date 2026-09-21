# ICS 499 Team 13 — Data Anonymization
## Scope Proposal (DRAFT for FP2 discussion)

**Status:** Draft. To be reviewed by both team members and discussed with Prof. Jasthi at the FP2 breakout session. Nothing here is final.

**Team:** Chris Nhul, Sophie Tony-Uduhirinwa
**Repo:** github.com/nhulchris/data_anonymizer

---

## 1. Problem Statement

Organizations need realistic data for development, testing, and analytics, but using production data exposes PII and creates regulatory risk (GDPR, HIPAA, PCI DSS). Assignment 2 produced a one-way, SQL-only anonymizer script. This project extends that work into a full application: multiple file formats, a menu of anonymization techniques, both one-way and reversible modes, and a usable interface.

## 2. Users and Stakeholders

- Developers / QA engineers who need production-like test data with PII removed
- Data analysts who need shareable datasets with reduced re-identification risk
- Prof. Jasthi (customer proxy / product owner)

## 3. Proposed Scope

### Dataset types
| Type | Priority | Notes |
|---|---|---|
| SQL dump (.sql) | Core | Parser exists from Assignment 2 |
| CSV | Core | Cheapest to add, widest use |
| JSON | Core | Nested structures add moderate effort |
| XLSX | Stretch | Only if time allows |

### Anonymization techniques
| Technique | Mode | Priority |
|---|---|---|
| Data substitution (Faker-realistic values) | One-way | Core (exists in A2) |
| Pseudonymization w/ consistent mapping within and across tables | One-way | Core (exists in A2) |
| Nulling / suppression | One-way | Core |
| Partial masking (j***@gmail.com, ***-***-1234) | One-way | Core |
| Hashing | One-way | Core |
| Generalization (DOB→year, ZIP→region, age→range) | One-way | Core |
| **Reversible anonymization** — encrypted mapping/key file that restores originals exactly | Two-way | Flagship |
| **Format-preserving masking** (output passes same validation as input) | One-way or two-way | Flagship |
| Data shuffling | One-way | Stretch |
| Numeric perturbation | One-way | Stretch |
| Synthetic dataset generation | N/A | Stretch |
| Free-text PII scanning | One-way | Stretch |

### Application shape
Core anonymization **engine** (independently unit-testable, TDD) + **web UI**: upload file → detected PII columns shown with technique per column (user-adjustable) → preview → download anonymized output, plus the re-identification key file when reversible mode is used.

## 4. Technology Stack — DECISION NEEDED

| Option | Description | Pros | Cons |
|---|---|---|---|
| A | Python engine + FastAPI backend, hosted on Render/Railway | Reuses A2 code and Faker | Second hosting platform; free-tier cold starts during demos |
| B | Full TypeScript/Next.js rewrite on Vercel | Native fit for existing Vercel setup | Discards working A2 code; JS faker ecosystem weaker |
| C | **Client-side processing in the browser** (JS engine, or A2 Python via Pyodide/WASM), static hosting on Vercel | Data never leaves the user's machine — strongest privacy design for a privacy tool; no server timeouts on large files; trivial hosting | Least familiar tech; feasibility spike required |

**Recommendation:** Option C if the FP2 feasibility spike succeeds; Option B as fallback. Decide as a team after the spike.

## 5. Definition of Done (acceptance criteria)

1. User can upload a .sql, .csv, or .json file and download a valid anonymized version (SQL re-parses; CSV/JSON round-trip cleanly).
2. PII columns are auto-detected (name-based) and the user can override detection and technique per column.
3. Identical source values map to identical anonymized values within and across tables.
4. Reversible mode restores the original dataset exactly, given the key file; without the key file, originals are not recoverable.
5. Engine has an automated test suite (TDD, run in CI) covering every shipped technique, including malformed-input cases.
6. Application is publicly deployed and demoable end-to-end.
7. Repo contains README, design document, original + anonymized sample datasets, and testing evidence.

## 6. Out of Scope

Dynamic (query-time) data masking; live production-database connectors; token-vault service infrastructure; enterprise key management; formal compliance certification (regulations inform design and documentation only); user accounts/authentication (pending instructor answer below).

## 7. Open Questions for Prof. Jasthi

1. Is Vercel an acceptable deployment target for this project (as it was for Assignment 1), or is Bluehost expected?
2. Is client-side (in-browser) processing acceptable, given the demo happens in a browser either way?
3. Any minimum expectation on number of techniques or dataset types?
4. Expected file sizes to support?
5. Are user accounts / multi-user features expected, or is a single-session tool sufficient?
