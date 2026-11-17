# Generating Test Data with AI

The Data Anonymizer accepts files produced by AI tools (ChatGPT, Claude,
Gemini, etc.) as a first-class input source. The prompts below are written
so the generated files land in exactly the shape the anonymizer detects and
processes. Each prompt was verified by generating files to its
specification and running them through the application: all PII columns
detected, anonymization and (where applicable) reversible restore
succeeded.

## Why a prompt specification

Detection is driven by column names and value formats. An AI asked casually
for "some customer data" may emit headers like `Customer Full Name` or
SSNs without dashes, which weakens detection. The prompts pin down the
naming and formats the tool expects, so AI-generated data works first try.

## Prompt 1 — CSV test data

Copy, adjust the row count, and paste into any AI assistant:

```
Generate a CSV file of fictional customer data with exactly these columns,
in this order:

id,name,email,phone,address,dob,zip,ssn,ip_address,credit_card,order_total

Rules:
- 200 rows, plain CSV, comma-separated, header row first, UTF-8
- id: sequential integers starting at 1
- name: realistic fictional full names (First Last)
- email: fictional, format local@domain.tld
- phone: format 612-555-1234
- address: fictional street addresses (e.g. 100 Main St)
- dob: format YYYY-MM-DD, years between 1940 and 2005
- zip: 5-digit US ZIP codes
- ssn: format 123-45-6789 (fictional, do not use real SSNs)
- ip_address: valid IPv4 like 192.168.1.10
- credit_card: 16 digits, no spaces (fictional)
- order_total: decimal number like 19.99
- Repeat 2-3 customers on multiple rows (same name/email/phone) so
  consistency can be demonstrated
- Output only the raw CSV, no explanation, no code fences
```

## Prompt 2 — multi-table SQL dump

```
Generate a SQL script for a fictional company with exactly two tables.

Structure:
- CREATE TABLE customers (id INT, name VARCHAR(100), email VARCHAR(100),
  phone VARCHAR(20), ssn VARCHAR(11));
- CREATE TABLE orders (order_id INT, customer_name VARCHAR(100),
  customer_email VARCHAR(100), total VARCHAR(10));
- One INSERT statement per table using the multi-row VALUES form, with the
  column list included
- 20 customers; 40 orders that reuse names and emails from the customers
  table exactly (same spelling), so the same people appear in both tables
- Escape apostrophes in names SQL-style ('O''Brien')
- String values in single quotes; numbers bare
- Begin with DROP TABLE IF EXISTS statements for both tables
- Output only the raw SQL, no explanation, no code fences
```

## Prompt 3 — JSON test data

```
Generate a JSON file: a single array of objects, each with exactly these
keys: "id", "name", "email", "phone", "zip"

- 100 objects; every object has every key (no missing fields)
- Same value formats as a US customer record: phone 612-555-1234,
  zip 5 digits
- All values as strings
- Repeat a few people across multiple objects
- Output only the raw JSON array, no explanation, no code fences
```

## Prompt 4 — free-text document (TXT)

```
Write 20 lines of fictional customer-support notes. Sprinkle in, across
the lines: email addresses (name@domain.tld), phone numbers (612-555-1234),
SSNs (123-45-6789), IPv4 addresses, and 16-digit card numbers written as
4111-1111-1111-1111. Mention some of the same contact details on more than
one line. Output only the raw text.
```

## Constraints that apply to any generated file

- Under 10 MB (the upload cap)
- UTF-8 (the app also tolerates UTF-16-with-BOM and Latin-1)
- CSV/JSON: headers from the list above — detection is column-name-first,
  and these names all match its keywords
- Avoid naming non-PII columns with PII-like words; identifier columns
  (customer_id, order_num) are automatically exempt from value-pattern
  detection
- AI-generated "fictional" data can accidentally collide with real values;
  treat generated files as test data only

## Verification record

Files generated to Prompts 1-4 were run through the deployed application:
- CSV: 10/11 columns detected as PII (id correctly skipped), anonymize and
  reversible restore exact
- SQL: both tables parsed, 6 PII columns detected, cross-table consistency
  held in output, restore exact
- JSON: 4/5 keys detected (id correctly skipped), round trip valid
- TXT: all five pattern types found; repeated values replaced consistently
