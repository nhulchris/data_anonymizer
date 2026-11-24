# Market Research — Existing Anonymization Tools

Landscape review informing Team 13's scope decisions during FP2;
formalized as a document at project close (FP10). Purpose: understand what
already exists, borrow proven ideas, and define the gap our tool fills.

## The tools

**Microsoft Presidio** (open source). PII *detection* engine for text and
images: NLP-based recognizers (names, locations) plus pattern recognizers,
with pluggable anonymizers. Strongest at finding PII in unstructured text —
exactly the NLP capability we scoped out of our TXT support. Detection-
first design; the user assembles the pipeline around it.

**ARX** (open source, academic). Desktop tool for formal privacy models —
k-anonymity, l-diversity, differential privacy — with risk-of-
re-identification analysis. The academic gold standard for *statistical*
anonymization of tabular datasets; heavyweight, Java GUI, steep learning
curve, no web workflow.

**Faker** (open source library). Realistic fake-value generation across
locales. Not an anonymizer by itself — no detection, no mapping, no file
handling — but the best-known generation engine. We use it as a component,
which is its intended role.

**Gretel** (commercial, API-first). Synthetic data generation using ML
models trained on the source data, plus transform/classify APIs. Cloud
service; data leaves your environment; priced per usage.

**Commercial enterprise tier — Tonic.ai, Delphix, K2view, Informatica.**
Production test-data-management platforms: connect to live databases,
subset and mask terabytes, maintain referential integrity across whole
schemas, enterprise contracts. This is the category our tool is a scaled-
down, file-based version of.

## Comparison

| Capability | Presidio | ARX | Faker | Gretel | Ours |
|---|---|---|---|---|---|
| Auto PII detection (structured) | Partial | No | No | Yes | Yes (column name + pattern) |
| Free-text PII detection | Yes (NLP) | No | No | Yes | Pattern-based only (documented) |
| Technique choice per column | Assemble yourself | Yes | No | Limited | Yes (10 techniques + Keep) |
| Consistent mapping across tables/files | Build yourself | N/A | No | Yes | Yes (shared seeded store) |
| Reversible with encrypted key | No | No | No | No | Yes (PBKDF2 + Fernet key file) |
| SQL dump in → valid SQL dump out | No | No | No | No | Yes |
| Web UI, zero install | No | No | No | Yes (cloud) | Yes |
| Data stays with operator | Yes (library) | Yes (desktop) | Yes | No (cloud API) | Yes (in-memory per request, no storage) |
| Cost | Free | Free | Free | Paid | Free |

## The gap we fill

No free tool in this list takes an ordinary file (CSV, JSON, SQL dump,
TXT), detects PII automatically, lets a non-programmer pick a technique
per column in a browser, keeps the same person consistent across tables
and files, and offers passphrase-protected reversibility — without
installing anything or sending data to a third-party cloud. Presidio and
Faker are libraries for developers; ARX is a statistician's desktop
application; Gretel is a paid cloud service; the enterprise platforms
assume live databases and procurement budgets. Ours is the teachable,
self-contained middle: the core mechanics of the enterprise tier
(detection, technique-per-field, referential consistency, controlled
re-identification) at classroom-to-small-team scale.

## What we borrowed

- Faker as the substitution engine (used as designed, as a component)
- Presidio's lesson that free-text PII needs NLP — which is why our TXT
  scope is honestly limited to pattern-detectable types
- The enterprise tier's deterministic/consistent masking concept, realized
  as our HMAC-seeded mapping store
- Tokenization-vault semantics, delivered without vault infrastructure via
  the encrypted key file
