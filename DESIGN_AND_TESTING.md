# Design, Approach, and Testing

ICS 499 Capstone — Team 13 Data Anonymizer

This document covers the anonymization techniques, file parsers, UI
integration, and testing built for this project. The engine ships ten
techniques in total. Sections 1 and 2 describe three of them (partial
masking, generalization, nulling) and the four file parsers (CSV, JSON,
SQL, TXT) in detail, and the last section explains why these ten were
chosen from the course reference.

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
   that aren't actual columns, and splitting only on commas outside
   parentheses so types like `DECIMAL(10,2)` stay in one piece.
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
output, across columns, across tables, and across runs — without needing a
lookup table shared between runs. Every parser and technique was tested
against this requirement directly (see below).

---

## 4. Testing

All testing uses `pytest` and is part of the project's automated test
suite (182 tests passing project-wide as of this write-up). Each piece
was built and verified in small, isolated steps before being combined.

| File | Tests | Covers |
|---|---|---|
| `tests/test_techniques.py` | 42 | All 9 PII types × 3 techniques, empty values, unknown PII types, malformed input (e.g. unrecognized date formats) |
| `tests/test_parsers.py` | 4 | JSON parse/serialize round-trip, missing-key handling, empty-array error handling |
| `tests/test_sql_parser.py` | 24 | Column extraction (including DECIMAL columns and composite keys), statement/value splitting with quotes and escaped apostrophes, multi-row parsing, comment stripping, full multi-table parse/serialize against realistic data, anonymized-value round trip |
| `tests/test_txt_parser.py` | 16 | Each PII pattern individually, multiple types in one text, no-PII text left unchanged, cross-call consistency with a shared store |

The table lists the tests for the techniques and parsers documented above.
The remaining tests cover the engine, API, reversible mode, batch upload,
pseudonymization and the newer techniques (see `SCALABILITY.md`).

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

## 5. UI Integration and End-to-End Testing

Beyond unit tests on individual functions, the full application was tested
by hand through the actual website, upload through download, against the
real FastAPI backend (`/api/detect`, `/api/anonymize`, `/api/restore`).

### UI work

The upload/review/download interface was redesigned for clarity: a
per-column technique picker with a live plain-language description and
example (e.g. "Hides part of the value — j.smith@gmail.com →
j*****@gmail.com"), a Technique Guide page explaining all ten supported
techniques, a Restore page for reversing an anonymized file given its key
file and passphrase, and a local (browser-only) History log of files
processed in the current session.

The interface's JavaScript was wired directly to the real backend
contract. File content is sent as base64 text rather than raw bytes — first
as a plain form field, and now as a file part — a detail that turned out to
matter (see the 403 finding below and the upload ceiling bug in section 6).

### End-to-end results, by format

All four supported formats were tested through the live interface, for
both one-way and reversible anonymization:

| Format | Detect → Anonymize → Download | Reversible → Restore |
|---|---|---|
| CSV | Working | Working |
| JSON | Working | Working |
| SQL | Working (multi-table, grouped by table in the UI) | Working |
| TXT | Working (pattern-detectable PII only) | Working |

### Bugs found and fixed during integration testing

1. **403 Forbidden on `.sql` uploads.** The hosting platform's edge
   firewall blocked raw request bodies that pattern-matched SQL syntax —
   which a legitimate `.sql` file upload naturally does. Fixed by sending
   file content as base64 text instead of raw bytes, which keeps the
   payload opaque to the pattern matcher. It was first sent as a plain
   form field; that caused a separate size problem, described in section 6,
   and it is now sent as a file part.
2. **TXT-mode layout bug.** The free-text review UI reused the same
   4-column grid built for tabular columns (checkbox + name + technique +
   example), but text-mode rows have no checkbox. Without one, the row's
   label text was forced into a ~22px-wide column meant for a checkbox,
   causing it to wrap one letter at a time. Fixed by giving text mode its
   own, simpler row layout instead of reusing the tabular one.
3. **Stale summary stats in TXT mode.** The "N of N protected" header and
   coverage bar are tabular-only concepts (they count columns), but they
   weren't being cleared when a `.txt` file was loaded, so they displayed
   leftover numbers from whatever was shown previously. Fixed by hiding
   that summary entirely in text mode and showing a plain match count
   instead.

### Correct rejections confirmed during testing (not bugs)

Two cases were initially mistaken for bugs but turned out to be the
backend correctly validating input:

- **Uploading the reversible `.zip` directly to Restore.** Reversible mode
  downloads a `.zip` containing two separate files (the anonymized data
  and an encrypted `.key` file); Restore expects those two files
  uploaded separately, not the zip itself. The server correctly returns
  400 for a `.zip` upload.
- **Reversible mode with an incompatible technique.** Only the
  store-backed techniques can be reversed (the full boundary is in the
  last section). Generalization and Partial Masking intentionally discard
  information and cannot be undone. Selecting one of those while
  Reversible is checked correctly returns a 422 with a specific, readable
  error naming exactly which technique isn't reversible.

The zip case now also has an in-page safeguard: selecting a `.zip` in
either Restore upload box shows a message telling the user to unzip it
first and upload the two files separately, instead of waiting for the
server to reject it.

---

## 6. Scale and Performance Testing

Following review feedback that the system should handle enterprise-scale
data, the SQL and JSON parsers were stress-tested directly in Python (not
through the website) against synthetic files that grew roughly 10x per
round. Testing the parsers directly separates "does the parser scale" from
"does the upload work", which mattered (see the upload finding below).

### Results

| Round | Format | Size | Scale | Parse | Anonymize | Serialize | Total |
|---|---|---|---|---|---|---|---|
| 1 | SQL | 4.2 MB | 120 tables, 30,000 rows | 3.29s | 0.22s | 2.01s | ~5.5s |
| 2 | SQL | 23.2 MB | 500 tables, 250,000 rows | 13.25s | 0.20s | 11.42s | ~24.9s |
| 3 | SQL | 234.6 MB | 1,000 tables, 2,500,000 rows | 140.17s | 1.07s | 125.27s | ~4.4 min |
| 1 | JSON | 8.3 MB | 50,000 rows | 0.14s | 0.04s | 0.14s | ~0.3s |
| 2 | JSON | 80 MB | 500,000 rows | 1.94s | 0.24s | 1.57s | ~3.8s |

JSON round 3 (5 million rows, about 800 MB) was generated but could not
be downloaded to the test machine, so JSON was verified through round 2
only.

### Findings

- **Parse and serialize scale roughly linearly.** From round 2 to round 3
  the SQL row count grew 10x, while parse time grew about 10.6x and
  serialize time about 11x. There is no sign of a performance cliff, and a
  234 MB, 2.5-million-row file completed without a crash or memory failure.
- **The anonymize timings are optimistic.** The generated files reused only
  about 100 to 400 distinct names, and repeated values are cheap lookups in
  the mapping store. Real data with mostly unique emails and SSNs is slower:
  the benchmark in `SCALABILITY.md` measured roughly 4,000 to 6,000 rows per
  second for fully distinct data. The parse and serialize numbers above
  carry over to real files; the anonymize numbers do not.
- **The live site's limits come from hosting, not the parsers.** The
  10 MB per-file cap is deliberate, and the free tier runs a single worker
  (documented in `SCALABILITY.md`).

### Upload ceiling bug

While generating test files, files well under the intended 10 MB cap were
rejected with "Part exceeded maximum size of 1024KB". Two near-identical
CSVs pinned the boundary: 717 KB raw succeeded and 819 KB raw failed. The
cause was the file content being sent as base64 text in a plain form
field. Base64 adds about 33%, and the web framework limits a form field to
about 1 MB, so the real ceiling was roughly 750 KB.

The finding was reported with the exact numbers and the base64-as-file-part
fix was made. After it, the 819 KB file and a 4.2 MB, 120-table SQL file
are both detected correctly, and files over 10 MB are rejected with a clear
message.

---

## 7. Post-Review Fixes and Additions

### Bug: SQL column parsing broke on DECIMAL(10,2)

`extract_columns` split a CREATE TABLE body on every comma, so
`amount DECIMAL(10,2)` produced a fake column named `2)`, and `serialize()`
then wrote invalid SQL. A composite `PRIMARY KEY (a, b)` caused the same
problem. Earlier tests missed it because they only covered a table with no
DECIMAL column.

**Fix:** a helper that splits only on commas outside parentheses and
quotes, plus two regression tests (column extraction, and a parse-serialize
round trip that produces valid SQL). Test suite: 177 passing at the time
of this fix (182 after the later detection fix below).

### Bug: ID columns were flagged as ZIP codes

On a large stress-test file, the value-pattern fallback in detection flagged
columns such as `customer_id` and `order_num` as ZIP codes, because their
values happened to be 5 digits. This produced false positives: 804 PII
columns detected, many of them not personal data. Column names were checked
first, but a column whose name matched nothing fell through to the value
pattern.

**Fix (Chris):** columns whose names end in an identifier suffix (id, key,
num, number, no, code, count, total, qty, index, idx, seq) now skip the
value-pattern fallback. The same file now detects 720 PII columns. The
per-column Keep option still covers any false positives that remain.
Test suite: 182 passing.

### Bug: technique descriptions went blank after changing a dropdown

The description lookup used display names ("Partial masking") but the
dropdown values had become backend names (`partial_masking`), so changing a
technique cleared its description and example. The four newest techniques
also had no descriptions. Fixed by mapping backend names to display names
and adding the missing entries.

### Keep (don't anonymize)

Each column's dropdown now includes a Keep option that leaves the column
unchanged. It works by excluding the column from the plan sent to the
backend, so no backend change was needed. Keep is deliberately absent from
the free-text (TXT) dropdown and the Settings default, where it has no
meaning.

### Batch tab

A new Batch tab uploads up to 20 files (CSV, JSON, SQL and TXT mixed) to
`/api/anonymize_batch`. One technique is applied to every detected column
in every file, and all files share one mapping store, so a person who
appears in several files gets the same fake value in each. In reversible
mode a single `batch.key` covers the whole batch.

The page checks files before sending: supported type, not empty, under
10 MB, no duplicate names, 20-file maximum. Verified manually with two CSVs
and one TXT file that share the same people: the fake names and emails
matched across all outputs, and a reversible run produced `batch.key`.

---

## 8. Known Limitations Summary

- **JSON:** headers are taken from the first record only; a field missing
  from record 1 but present later is dropped.
- **SQL:** only `INSERT` statement values are anonymized; other statement
  types pass through unchanged even if they contain PII.
- **TXT:** only pattern-detectable PII is found; names and addresses in
  free text are not detected (would require NLP; stretch goal).
- **Generalization:** not implemented for addresses (no reliable
  city/state extraction from free-form text).
- **Column override:** `/api/detect` only reports columns it flags as
  PII; it does not return the full column list. This means a user
  currently cannot manually flag a column the detector missed, since the
  interface has nothing to offer them to select. Supporting this would
  require a backend change to return all columns, not only the detected
  ones.
- **Batch mode:** applies one technique to all files; per-column choices
  are single-file only. Limits are 10 MB per file and 20 files per batch.
- **Upload size:** 10 MB per file by design. Larger files would need
  streaming or background processing (see `SCALABILITY.md`).
- **Hosting:** the free-tier host runs one worker, so simultaneous users
  queue (see `SCALABILITY.md`).

## Technique Scope: Why These Ten (added FP6, Chris)

The course reference lists 14+ anonymization techniques. We implement ten,
chosen so every distinct mechanism is represented: realistic replacement
(substitution), opaque identifiers (pseudonymization), one-way hashing,
suppression (nulling), partial masking, precision reduction (generalization),
format-preserving masking, record reordering (shuffling), statistical noise
(perturbation), and fully artificial generation (synthetic).

The four we deliberately excluded, and why:

- Static data masking: the category our tool implements, not a separate
  technique -- every one-way technique we ship is static masking.
- Dynamic data masking: masks at query time against a live production
  database. Our tool is a file-processing pipeline by design; there is no
  query layer to mask. Architectural mismatch, not a missing feature.
- Tokenization: requires a secure token-vault service. Our pseudonymization
  provides the same consistent-identifier property without vault
  infrastructure, and the encrypted key file covers tokenization's
  recover-the-original use case.
- Encryption as a field transform: encrypting a field makes data useless for
  the testing/analytics purposes anonymization serves. Where encryption
  belongs in our design, we use it -- protecting the reversal mapping
  (PBKDF2 + Fernet).

Reversibility boundary: substitution, pseudonymization, hashing, and
format-preserving masking are store-backed and reversible via the key file.
Nulling, masking, and generalization destroy information; shuffling breaks
the row-value link; perturbation and synthetic replace values without a
recoverable mapping. Those six are one-way, and the UI/API enforce that
boundary in reversible mode.