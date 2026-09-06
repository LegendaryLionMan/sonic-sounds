"""scripts/log-tail - structured log viewer for the daemon.

Usage:
    python scripts/log-tail                 # tail -f equivalent (Ctrl-C to stop)
    python scripts/log-tail --last 100      # show last 100 lines
    python scripts/log-tail --grep ERROR    # filter by pattern
    python scripts/log-tail --stats        # log level histogram + recent errors

The daemon writes to .meta/daemon.log (rotating) and a per-process
stdout/stderr file at C:/Users/lion_/AppData/Local/Temp/sonic-sounds-smoke/daemon-stdout.log.

This script gives you a colored, filtered view of either source.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

DEFAULT_LOG = Path(r"C:\dev\sonic-sounds\.meta\daemon.log")
ALT_LOG = Path(r"C:\Users\lion_\AppData\Local\Temp\sonic-sounds-smoke\daemon-stdout.log")

LEVEL_COLORS = {
    "ERROR": "\033[31m",   # red
    "WARNING": "\033[33m", # yellow
    "INFO": "\033[36m",    # cyan
    "DEBUG": "\033[90m",   # gray
}
RESET = "\033[0m"
USE_COLOR = sys.stdout.isatty()  # only color when interactive


def colorize(level: str, text: str) -> str:
    if not USE_COLOR or level not in LEVEL_COLORS:
        return text
    return f"{LEVEL_COLORS[level]}{text}{RESET}"


def parse_line(line: str) -> tuple[str, str] | None:
    """Extract (level, message) from a daemon log line. Format:
    2026-09-06 11:24:00,123 [name] LEVEL: msg
    """
    m = re.match(
        r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,\d]*\s+\[[^\]]+\]\s+(\w+):\s*(.*)$",
        line.rstrip("\n"),
    )
    if not m:
        return None
    return m.group(1), m.group(2)


def show_last(path: Path, n: int, pattern: str | None) -> None:
    if not path.exists():
        print(f"log not found: {path}")
        return
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    selected = lines[-n:] if len(lines) > n else lines
    for line in selected:
        if pattern and pattern not in line:
            continue
        parsed = parse_line(line)
        if parsed:
            level, msg = parsed
            ts = line[:19]
            print(f"{ts} {colorize(level, level.ljust(7))} {msg}")
        else:
            print(line.rstrip())


def show_stats(path: Path, n: int = 500) -> None:
    if not path.exists():
        print(f"log not found: {path}")
        return
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    sample = lines[-n:] if len(lines) > n else lines
    level_counts: Counter = Counter()
    errors: list[str] = []
    for line in sample:
        parsed = parse_line(line)
        if parsed:
            level, msg = parsed
            level_counts[level] += 1
            if level == "ERROR":
                errors.append(msg[:120])
    print(f"=== last {len(sample)} lines of {path.name} ===")
    for level in ("ERROR", "WARNING", "INFO", "DEBUG"):
        c = level_counts.get(level, 0)
        print(f"  {colorize(level, level.ljust(7))}: {c}")
    if errors:
        print(f"\n=== last {min(5, len(errors))} error(s) ===")
        for e in errors[-5:]:
            print(f"  {e}")


def follow(path: Path, pattern: str | None) -> None:
    if not path.exists():
        print(f"log not found: {path}")
        return
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        # Seek to end (like `tail -f`)
        f.seek(0, 2)
        try:
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.2)
                    continue
                if pattern and pattern not in line:
                    continue
                parsed = parse_line(line)
                if parsed:
                    level, msg = parsed
                    ts = line[:19]
                    print(f"{ts} {colorize(level, level.ljust(7))} {msg}")
                else:
                    print(line.rstrip())
        except KeyboardInterrupt:
            print("\n(interrupted)")


def main() -> int:
    p = argparse.ArgumentParser(description="sonic-sounds daemon log viewer")
    p.add_argument("--path", type=Path, default=None,
                   help=f"log path (default: {DEFAULT_LOG})")
    p.add_argument("--last", type=int, default=0,
                   help="show last N lines (0 = tail -f mode)")
    p.add_argument("--grep", type=str, default=None,
                   help="filter lines containing this pattern")
    p.add_argument("--stats", action="store_true",
                   help="print level histogram + recent errors")
    args = p.parse_args()

    path = args.path or (DEFAULT_LOG if DEFAULT_LOG.exists() else ALT_LOG)
    if not path.exists():
        print(f"log not found at {path}")
        return 1
    if args.stats:
        show_stats(path)
    elif args.last > 0:
        show_last(path, args.last, args.grep)
    else:
        follow(path, args.grep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
