"""Row-scale benchmark: engine throughput and memory at increasing sizes.

Run:  python benchmarks/benchmark_engine.py
Writes a markdown table to stdout. Used to produce the numbers in
SCALABILITY.md. Engine-level only (no HTTP): measures the anonymization
pipeline itself. 1M rows exceeds the web app's 10MB upload cap and is
included to show where the engine itself stands.
"""

from __future__ import annotations

import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.mapping import MappingStore  # noqa: E402
from engine.pipeline import build_plan, run  # noqa: E402
from parsers import csv_parser  # noqa: E402

SIZES = [10, 1_000, 10_000, 100_000]


def make_csv(rows: int, distinct: int | None = None) -> str:
    """distinct caps the number of unique people: real datasets repeat
    values, and engine cost scales with DISTINCT values (the mapping),
    not raw row count."""
    d = distinct or rows
    return "\n".join(
        ["id,name,email,phone,order_total"]
        + [
            f"{i},Person Number{i % d},user{i % d}@example.com,612-555-{i % 10000:04d},{(i % 500) + 0.99}"
            for i in range(rows)
        ]
    )


def bench(rows: int, technique: str = "substitution", distinct: int | None = None, memory: bool = True) -> dict:
    text = make_csv(rows, distinct)
    size_mb = len(text) / 1e6

    t0 = time.perf_counter()
    headers, data = csv_parser.parse(text)
    t_parse = time.perf_counter() - t0

    plan = build_plan(headers, data)
    for p in plan:
        p.technique = technique

    # Timing pass (tracemalloc off: it slows execution ~15x)
    t0 = time.perf_counter()
    result = run(headers, data, plan, MappingStore(seed="bench"))
    t_anon = time.perf_counter() - t0

    # Memory pass, separate, on a fresh store (skipped for the largest
    # runs: tracemalloc multiplies runtime ~15x)
    peak = 0
    if memory:
        tracemalloc.start()
        run(headers, data, plan, MappingStore(seed="bench-mem"))
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    t0 = time.perf_counter()
    out = csv_parser.serialize(result.headers, result.rows)
    t_ser = time.perf_counter() - t0

    return {
        "rows": rows,
        "size_mb": size_mb,
        "parse_s": t_parse,
        "anon_s": t_anon,
        "serialize_s": t_ser,
        "total_s": t_parse + t_anon + t_ser,
        "peak_mb": peak / 1e6,
        "rows_per_s": rows / t_anon if t_anon else 0,
        "out_mb": len(out) / 1e6,
    }


if __name__ == "__main__":
    technique = sys.argv[1] if len(sys.argv) > 1 else "substitution"
    print(f"Technique: {technique}\n")
    print("| Rows | File size | Parse | Anonymize | Serialize | Total | Peak extra RAM | Rows/sec |")
    print("|---|---|---|---|---|---|---|---|")
    runs = [(n, None, True) for n in SIZES] + [(1_000_000, 50_000, False)]
    for n, distinct, memory in runs:
        r = bench(n, technique, distinct, memory)
        r["label"] = f"{n:,}" + (f" ({distinct:,} distinct)" if distinct else "")
        print(
            f"| {r['label']} | {r['size_mb']:.1f} MB | {r['parse_s']:.2f}s "
            f"| {r['anon_s']:.2f}s | {r['serialize_s']:.2f}s | {r['total_s']:.2f}s "
            f"| {r['peak_mb']:.0f} MB | {r['rows_per_s']:,.0f} |"
        )
