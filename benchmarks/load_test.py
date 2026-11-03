"""Concurrent-user load test against the deployed site.

Run from any machine with Python + requests:
    pip install requests
    python benchmarks/load_test.py https://data-anonymizer-g90k.onrender.com

Simulates N simultaneous users each uploading and anonymizing a ~1,000-row
CSV, ramping N up per round. Reports per-round latency and errors. Stop
reading results at the first round with errors or runaway latency — that's
the capacity number for the report.

Note: warm the service first (open /api/health in a browser) so cold-start
time doesn't pollute round 1.
"""

from __future__ import annotations

import base64
import concurrent.futures
import statistics
import sys
import time

import requests

ROUNDS = [1, 2, 5, 10, 15, 20]
ROWS = 1_000
TIMEOUT = 120


def make_payload() -> dict:
    csv = "\n".join(
        ["id,name,email,phone"]
        + [f"{i},Person {i},u{i}@example.com,612-555-{i % 10000:04d}" for i in range(ROWS)]
    )
    b64 = base64.b64encode(csv.encode()).decode()
    return {"b64": b64}


def one_request(base_url: str, payload: dict) -> tuple[float, int | str]:
    t0 = time.perf_counter()
    try:
        r = requests.post(
            f"{base_url}/api/anonymize",
            data={"filename": "load.csv"},
            files={"content_file": ("content.b64", payload["b64"].encode())},
            timeout=TIMEOUT,
        )
        return time.perf_counter() - t0, r.status_code
    except requests.RequestException as e:
        return time.perf_counter() - t0, type(e).__name__


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    base_url = sys.argv[1].rstrip("/")
    payload = make_payload()

    print(f"Target: {base_url}  |  payload: {ROWS:,} rows per request\n")
    print("| Concurrent users | OK | Errors | Fastest | Median | Slowest |")
    print("|---|---|---|---|---|---|")
    for n in ROUNDS:
        with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
            results = list(pool.map(lambda _: one_request(base_url, payload), range(n)))
        times = [t for t, s in results]
        ok = sum(1 for _, s in results if s == 200)
        errors = [s for _, s in results if s != 200]
        print(
            f"| {n} | {ok}/{n} | {', '.join(map(str, errors)) or '-'} "
            f"| {min(times):.1f}s | {statistics.median(times):.1f}s | {max(times):.1f}s |"
        )
        time.sleep(3)  # let the single instance breathe between rounds


if __name__ == "__main__":
    main()
