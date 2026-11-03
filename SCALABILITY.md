# Scalability and Limits

Team 13 — findings from stress-testing the Data Anonymizer as if it were a
production system, per instructor direction (FP6 review). Numbers are
measured, not estimated. Two real defects were found and fixed during this
work; both are documented below because finding them was the point.

## 1. Defects found by stress testing (both fixed)

**Upload ceiling was 12x lower than designed.** The 10 MB upload cap was
never reachable: the web framework caps a text form field at 1 MB, and our
base64 transport (required to get past the host's edge firewall) inflates
files by ~33%, so real files failed at roughly 750-800 KB with a misleading
error. Found by uploading progressively larger files (817 KB failed, 717 KB
passed). Fixed by sending the base64 payload as a *file* part, which
streams to disk with no field cap. The 10 MB application cap is now the
true limit, verified by test.

**Reversibility silently degraded at scale.** At ~65,000 distinct names,
the fake-name generator started assigning the same fake to two different
originals (birthday-problem collisions against Faker's finite name pool),
and restore correctly refused the ambiguous mapping — meaning large
reversible jobs could not be restored at all. Fixed with collision-aware
generation: the mapping store tracks fakes in use and generation retries
deterministically until unique, with a deterministic suffix fallback if the
pool is ever exhausted. A 65,000-row full anonymize-and-restore round trip
now passes in CI.

## 2. Row-scale performance (engine, measured)

Technique: substitution (the most expensive store-backed technique).
Hardware: CI sandbox; Render free tier is slower — treat relative shape as
the finding, not absolute times.

| Rows | File size | Parse | Anonymize | Serialize | Total | Peak extra RAM | Rows/sec |
|---|---|---|---|---|---|---|---|
| 10 | 0.0 MB | 0.00s | 0.00s | 0.00s | 0.00s | 0 MB | 5,723 |
| 1,000 | 0.1 MB | 0.00s | 0.17s | 0.00s | 0.17s | 1 MB | 5,921 |
| 10,000 | 0.6 MB | 0.01s | 1.97s | 0.01s | 1.98s | 10 MB | 5,089 |
| 100,000 | 6.6 MB | 0.09s | 22.97s | 0.10s | 23.17s | 66 MB | 4,353 |
| 1,000,000 (50,000 distinct) | 67.2 MB | 1.49s | 12.52s | 0.97s | 14.98s | — | 79,869 |

Reproduce with `python benchmarks/benchmark_engine.py`.

Key insights:

- **Cost scales with distinct values, not rows.** A million rows with
  realistic repetition (50k distinct people) processes in ~15s at ~80k
  rows/sec, because repeated values are store lookups. A fully-distinct
  100k-row file takes longer than a 1M-row realistic one.
- **Throughput degrades gracefully as the name pool saturates** (measured
  ~12k/s at 10k distinct names down to ~8k/s at 50k) due to collision
  retries — expected and bounded.
- **Memory is linear and modest**: ~66 MB extra at 100k rows, comfortably
  inside the host's 512 MB. The 10 MB upload cap keeps memory bounded by
  design; files are processed fully in memory.
- **The practical ceiling is the web layer, not the engine.** A
  fully-distinct 100k-row file needs ~23s of compute before network
  overhead, approaching typical request-timeout windows. Within the 10 MB
  cap this stays workable; beyond it is background-job territory (below).

## 3. Concurrent users (live site, measured)

Run `python benchmarks/load_test.py https://data-anonymizer-g90k.onrender.com`
— ramps 1 → 20 simultaneous users each anonymizing a 1,000-row CSV and
reports latency/errors per level.

RESULTS TO BE FILLED IN FROM THE LIVE RUN:

| Concurrent users | OK | Errors | Fastest | Median | Slowest |
|---|---|---|---|---|---|
| (paste load_test.py output here) | | | | | |

Expectation to verify: the free tier runs a single instance with one
worker, so concurrent requests serialize — latency should grow roughly
linearly with user count until requests time out. The capacity number for
the report is the last round with zero errors.

## 4. Multiple files

`/api/anonymize_batch` accepts up to 20 files in one request (CSV, JSON,
SQL, TXT mixed), processed with one shared mapping store, so the same
person appearing across files receives the same fake in all of them —
verified by test, including a batch-wide single key file in reversible
mode.

## 5. Current limits (by design, documented)

- 10 MB per file; 20 files per batch request
- One request = one job: no progress bar, no cancellation, no resume
- Free-tier hosting: single instance, cold starts after idle (~50s),
  compute roughly 2-5x slower than the benchmark hardware
- Encodings: UTF-8 (with/without BOM), UTF-16 with BOM, Latin-1 fallback
- Per-column technique plans are single-file mode; batch mode applies one
  technique to all detected columns

## 6. What production deployment would change (future work, not built)

- Streaming/chunked processing to lift the in-memory 10 MB ceiling
- A job queue with background workers for long-running files, replacing
  the synchronous request model (also fixes head-of-line blocking)
- Horizontal scaling behind a load balancer; paid-tier instances
- Observability: metrics, alerting, structured logs (currently: host logs)
- Rate limiting and per-user isolation (no user model in scope)
