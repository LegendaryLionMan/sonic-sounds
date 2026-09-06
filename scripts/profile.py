"""scripts/profile - request profiler for the daemon.

Usage:
    python scripts/profile                # start daemon with profiling
    python scripts/profile --stop         # stop profiling, dump report
    python scripts/profile --report       # read last report

The daemon's @app.before_request / @app.after_request hooks (defined
in scripts/profile_patch.py) capture timing data into a JSON file at
.meta/profile.json. This script:
  - On --stop / Ctrl-C: stops the daemon, reads .meta/profile.json, and
    prints a top-20-by-time table grouped by route.
  - On --report: just reads the last report without restarting.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE_PATH = ROOT / ".meta" / "profile.json"


def analyze(path: Path) -> str:
    if not path.exists():
        return f"(no profile data at {path})"
    data = json.loads(path.read_text(encoding="utf-8"))
    samples = data.get("samples", [])
    if not samples:
        return "(no samples recorded)"

    # Group by route
    by_route: dict[str, list[dict]] = {}
    for s in samples:
        r = s.get("route", "?")
        by_route.setdefault(r, []).append(s)

    lines = []
    lines.append(f"=== profile: {len(samples)} samples across {len(by_route)} routes ===")
    rows = []
    for route, ss in by_route.items():
        durations = [x["duration_ms"] for x in ss]
        rows.append({
            "route": route,
            "count": len(durations),
            "total_ms": sum(durations),
            "avg_ms": sum(durations) / len(durations),
            "max_ms": max(durations),
            "p95_ms": sorted(durations)[int(len(durations) * 0.95)] if len(durations) >= 20 else max(durations),
        })
    rows.sort(key=lambda r: r["total_ms"], reverse=True)
    lines.append(f"{'route':<40} {'count':>6} {'total_ms':>10} {'avg':>8} "
                 f"{'max':>8} {'p95':>8}")
    lines.append("-" * 84)
    for r in rows[:20]:
        lines.append(
            f"{r['route']:<40} {r['count']:>6} {r['total_ms']:>10.1f} "
            f"{r['avg_ms']:>8.1f} {r['max_ms']:>8.1f} {r['p95_ms']:>8.1f}"
        )
    # Top 5 slowest single requests
    lines.append("")
    lines.append("=== top 5 slowest requests ===")
    slowest = sorted(samples, key=lambda s: s["duration_ms"], reverse=True)[:5]
    for s in slowest:
        lines.append(f"  {s['duration_ms']:>8.1f}ms  {s['route']}  ({s.get('method', '?')} {s.get('status', '?')})")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="daemon profiler reader")
    p.add_argument("--report", action="store_true",
                   help="print report from last profile run")
    args = p.parse_args()
    print(analyze(PROFILE_PATH))
    return 0


if __name__ == "__main__":
    sys.exit(main())
