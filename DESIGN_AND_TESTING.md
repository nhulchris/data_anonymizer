# Design, Approach, and Testing 

ICS 499 Capstone — Team 13 Data Anonymizer

This document covers the anonymization techniques, file parsers, and testing
built for this project: three anonymization techniques (partial masking,
generalization, nulling) and four file parsers (CSV, JSON, SQL, TXT).

---

## 1. Anonymization Techniques

All techniques implement a shared `Technique` interface
(`engine/techniques/base.py`): `anonymize(pii_type, value, store)` takes a
PII type and a real value, and returns a replacement value. Every technique
is registered with the engine's registry so it appears automatically in the
app's technique dropdown.

### Partial Masking

Hides part of a value while keeping its format recognizable, for example
`john.smith@gmail.com` → `j**********@gmail.com`, or `123-45-6789` →
`***-**-6789`. Each of the 9 supported PII types (name, email, phone,
address, dob, zip, ssn, ip, card) has its own masking rule, since a
sensible mask looks different for each type.

**Design decision:** date-of-birth masking needed its own logic rather than
the generic "keep the last 4 digits" approach used for phone/ssn/card,
because a date's last 4 characters don't reliably correspond to the year
across different formats (`YYYY-MM-DD` vs `MM/DD/YYYY`). A dedicated
`_mask_dob()` helper detects the format first, then masks the month and day
while preserving the year.

### Generalization

Reduces precision while keeping the value useful: a date of birth becomes
just the year, a ZIP code keeps its first 3 digits (`55401` → `554XX`), a
card number keeps its first 6 digits (the bank-identifying BIN/IIN) and
masks the rest.

**Design decision:** address generalization is intentionally left
unimplemented (the original value passes through unchanged). Reliably
extracting a city or state from arbitrary, unstructured address text is a
language-processing problem, not a formatting one, and was judged out of
scope. This is documented so a user choosing generalization for an address
column knows what to expect.

### Nulling

Suppresses the value entirely, returning an empty string regardless of PII
type. The simplest of the three, and useful as a baseline for comparison
against the other techniques.

---

## 2. File Parsers

Each parser follows the same basic contract as the others in the project:
turn a file's raw text into a simple data structure the anonymization
engine can work with, and turn it back into valid output text afterward.

### CSV (`parsers/csv_parser.py`)

Reference implementation. `parse()` reads CSV text into `(headers, rows)`;
`serialize()` writes it back.

### JSON (`parsers/json_parser.py`)

Reads a JSON array of objects into the same `(headers, rows)` shape used by
CSV, so the rest of the pipeline doesn't need to know which format it came
from. Headers are taken from the first object's keys; later objects
missing a key get an empty string for that field.

**Design decision / known limitation:** because headers come only from the
first record, a field present in a later record but absent from the first
is silently dropped rather than added as a new column. This is a
deliberate simplification — a more robust version would scan every record
first to build the complete header set.

### SQL (`parsers/sql_parser.py`)

The most involved parser, since a SQL file isn't naturally tabular the way
CSV/JSON are: it can contain multiple tables, multiple `INSERT` statements
per table, and non-data statements (`DROP`, `CREATE`, `UPDATE`, `DELETE`,
comments) that must not be touched.

**Approach**, built and tested in stages:

1. `strip_comments()` — removes `--` line comments, respecting quoted
   strings (so a comment marker's not confused with one inside real data).
2. `split_statements()` — splits the file into individual statements,
   tracking whether the scanner is inside a quoted string so a semicolon
   *inside* a value (e.g. `'Call me; it's urgent'`) isn't mistaken for the
   end of a statement.
3. `extract_columns()` — pulls column names out of a `CREATE TABLE`
   statement, skipping constraint lines (`PRIMARY KEY`, `FOREIGN KEY`, etc.)
   that aren't actual columns.
4. `extract_row_groups()` — splits a multi-row `VALUES (...), (...), (...)`
   list into individual rows, tracking parenthesis depth and quotes so a
   comma inside a quoted address (`'123 Main St, Minneapolis, MN'`) doesn't
   split a row apart.
5. `split_values()` — splits one row into its individual field values, same
   quote-tracking approach, and un-escapes SQL's doubled-apostrophe format
   (`O''Connor` → `O'Connor`).
6. `parse()` — ties it together: reads the whole file once, and returns a
   list of tables, each `{"name", "headers", "rows"}`, matching the same
   shape CSV/JSON use (per team agreement on the multi-table design).
7. `serialize()` — rebuilds the file: `CREATE TABLE`, `DROP`, `UPDATE`,
   `DELETE`, and comments pass through unchanged; `INSERT` statements are
   rebuilt from the (possibly anonymized) row data.

**Design decision:** only `INSERT` statement values are anonymized. Other
statement types are out of scope for this version — if a `DELETE`/`UPDATE`
statement happened to contain PII in its own text, it would not be caught.
This matches the project's agreed v1 scope.

**Bug found and fixed during testing:** an early version of `parse()` and
`serialize()` worked correctly on hand-written test SQL but returned zero
rows against the actual assignment test file. The cause: the real file has
`-- comment` lines directly above several `INSERT` statements, and because
SQL comments don't end with a semicolon, the comment text was getting
glued onto the following statement, which then no longer started with
`INSERT INTO` and was skipped entirely. `strip_comments()` was added to fix
this — it's now the first step in both `parse()` and `serialize()`.

### TXT (`parsers/txt_parser.py`)

**Scope** (per team agreement): TXT support is limited to
pattern-detectable PII — email, phone, SSN, IP address, and card number.
Detecting names and addresses in unstructured free text would require
natural-language processing and was agreed to be a stretch goal, not part
of this version.

**Approach:** `find_matches()` scans the text with a regex pattern per PII
type, checked in a specific order (email, SSN, card, IP, phone) so a more
specific pattern claims a match before a looser one can — for example, a
16-digit card number is caught as `card` before the phone pattern could
match part of it. Overlapping matches are resolved by first-match-wins.
`anonymize_text()` then walks through the matches and replaces each one
using the chosen technique and the shared `MappingStore`, so the same value
gets the same replacement everywhere, consistent with how CSV/JSON/SQL
handle repeated values.

---

## 3. Consistency

All four parsers and all three techniques rely on the same mechanism for
consistency: `MappingStore` (`engine/mapping.py`, built by Chris) keys its
mappings by `(pii_type, original_value)` and derives a per-value seed from
a project seed using HMAC, so the same input always produces the same
output, across columns, across tables, and across runs — without storing a
reversible mapping or needing a lookup table shared between runs. Every
parser and technique was tested against this requirement directly (see
below).

---

## 4. Testing

All testing uses `pytest` and is part of the project's automated test
suite (109 tests passing project-wide as of this write-up). Each piece
was built and verified in small, isolated steps before being combined.

| File | Tests | Covers |
|---|---|---|
| `tests/test_techniques.py` | 43 | All 9 PII types × 3 techniques, empty values, unknown PII types, malformed input (e.g. unrecognized date formats) |
| `tests/test_parsers.py` | 4 | JSON parse/serialize round-trip, missing-key handling, empty-array error handling |
| `tests/test_sql_parser.py` | 22 | Column extraction, statement/value splitting with quotes and escaped apostrophes, multi-row parsing, comment stripping, full multi-table parse/serialize against realistic data, anonymized-value round trip |
| `tests/test_txt_parser.py` | 16 | Each PII pattern individually, multiple types in one text, no-PII text left unchanged, cross-call consistency with a shared store |

**Testing evidence beyond unit tests:** the SQL parser was additionally run
against the project's actual Assignment-2-style test file (4 tables, 2
`INSERT` statements for one table, apostrophes, commas inside addresses) —
both to parse it (confirming correct table and row counts) and to produce
a real anonymized output file, verified directly on disk (not just in
memory) to contain the replacement values.

### Testing approach notes

- Each function was tested in isolation before being combined with others,
  so a failure could be traced to a specific step rather than the whole
  pipeline.
- Edge cases were tested deliberately, not just the "happy path": empty
  values, missing fields, malformed dates, SSN-shaped numbers that
  shouldn't double-match as phone numbers, blank JSON arrays.
- One test itself was found to be wrong during this process (asserting a
  value was anonymized everywhere in a file, when it had only been
  anonymized in one of several tables that happened to share that value) —
  corrected once the actual, correct behavior was confirmed by inspecting
  the output directly.

---

## 5. Known Limitations Summary

- **JSON:** headers are taken from the first record only; a field missing
  from record 1 but present later is dropped.
- **SQL:** only `INSERT` statement values are anonymized; other statement
  types pass through unchanged even if they contain PII.
- **TXT:** only pattern-detectable PII is found; names and addresses in
  free text are not detected (would require NLP; stretch goal).
- **Generalization:** not implemented for addresses (no reliable
  city/state extraction from free-form text).