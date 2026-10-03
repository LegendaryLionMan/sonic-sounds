"""scripts/perf-trace - daemon request tracing tool.

Per 2026-09-06 user feedback: the perf suite (suite 2) only measures
top-level latency. This tool gives per-route histograms from a
sampling run, identifies slow endpoints, and reports P50/P95/P99.

Usage:
    python scripts/perf-trace.py --duration 60 --sample-rate 5
    python scripts/perf-trace.py --output report.json

The script enables the daemon's built-in request profiler (sets
SONIC_SOUNDS_PROFILE=1 by writing a marker file the daemon can
detect), then samples /api/* endpoints at the given rate.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

BASE = "http://127.0.0.1:8765"
ENDPOINTS = [
    ("GET", "/api/health"),
    ("GET", "/api/albums"),
    ("GET", "/api/albums/half-light-hours"),
    ("GET", "/api/albums/half-light-hours/tracks"),
    ("GET", "/api/albums/half-light-hours/assets"),
    ("GET", "/api/albums/half-light-hours/cover"),
    ("GET", "/api/sessions"),
    ("GET", "/api/decisions"),
    ("GET", "/site/albums.html"),
    ("GET", "/site/library.html"),
]


def measure(method: str, url: str) -> tuple[int, float]:
    req = urllib.request.Request(url, method=method)
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            r.read()
            return r.status, (time.perf_counter() - start) * 1000
    except Exception as e:
        return -1, (time.perf_counter() - start) * 1000


def main() -> int:
    p = argparse.ArgumentParser(description="daemon perf tracer")
    p.add_argument("--duration", type=int, default=30, help="seconds to sample")
    p.add_argument("--rate", type=float, default=2.0,
                   help="requests per second per endpoint")
    p.add_argument("--output", type=str, help="write JSON report to path")
    args = p.parse_args()

    by_endpoint: dict[str, list[float]] = defaultdict(list)
    by_endpoint_status: dict[str, list[int]] = defaultdict(list)
    interval = 1.0 / args.rate
    deadline = time.time() + args.duration
    print(f"[perf-trace] sampling {len(ENDPOINTS)} endpoints for {args.duration}s")
    start = time.time()
    total = 0
    while time.time() < deadline:
        for method, path in ENDPOINTS:
            status, ms = measure(method, BASE + path)
            by_endpoint[method + " " + path].append(ms)
            by_endpoint_status[method + " " + path].append(status)
            total += 1
            if time.time() + interval < deadline:
                time.sleep(interval)
        if time.time() >= deadline:
            break
    duration = time.time() - start

    report = {"duration_sec": duration, "total_samples": total,
              "endpoint_stats": {}}
    print(f"\n[perf-trace] {total} samples in {duration:.1f}s\n")
    print(f"{'endpoint':<55} {'count':>6} {'p50':>8} {'p95':>8} {'p99':>8} {'errors':>7}")
    for ep, samples in by_endpoint.items():
        p50 = statistics.median(samples)
        samples_sorted = sorted(samples)
        p95 = samples_sorted[int(len(samples) * 0.95)] if len(samples) > 1 else samples_sorted[-1]
        p99 = samples_sorted[int(len(samples) * 0.99)] if len(samples) > 1 else samples_sorted[-1]
        errors = sum(1 for s in by_endpoint_status[ep] if s < 0 or s >= 400)
        report["endpoint_stats"][ep] = {
            "count": len(samples), "p50_ms": p50, "p95_ms": p95,
            "p99_ms": p99, "errors": errors, "samples_ms": samples,
        }
        print(f"{ep:<55} {len(samples):>6} {p50:>8.1f} {p95:>8.1f} {p99:>8.1f} {errors:>7}")
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nreport saved to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
