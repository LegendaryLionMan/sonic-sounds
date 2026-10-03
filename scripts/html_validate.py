"""scripts/html-validate - HTML lint runner.

Per 2026-09-06 user feedback: the visual inspection found that
album.html has duplicate IDs (multiple instances of album-cover-large
etc. when the page is rendered twice). html-validate catches duplicate
IDs, missing required attributes, and malformed markup.

This is a lightweight wrapper that just shells out to the html5validator
or html-validate npm package, whichever is available.

Usage:
    python scripts/html-validate.py
    python scripts/html-validate.py --page intake.html
    python scripts/html-validate.py --strict

Requirements:
    npm install -g html-validate
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALL_PAGES = ["albums.html", "studio.html", "intake.html", "library.html",
             "dashboard.html", "album.html", "index.html"]


def find_html_validator() -> str | None:
    return shutil.which("html-validate") or shutil.which("html5validator")


def main() -> int:
    p = argparse.ArgumentParser(description="HTML lint")
    p.add_argument("--page", action="append", help="specific page (repeatable)")
    p.add_argument("--strict", action="store_true",
                   help="exit non-zero on any error")
    args = p.parse_args()

    validator = find_html_validator()
    if not validator:
        print("[html-validate] no validator binary found.")
        print("  install: npm install -g html-validate")
        return 1

    pages = args.page or ALL_PAGES
    total_errors = 0
    for path in pages:
        full = ROOT / "site" / path
        if not full.exists():
            print(f"[html-validate] missing: {path}")
            continue
        result = subprocess.run(
            [validator, str(full)],
            capture_output=True, text=True, timeout=30,
        )
        errors = sum(1 for line in result.stdout.splitlines()
                     if "error" in line.lower())
        warnings = sum(1 for line in result.stdout.splitlines()
                       if "warning" in line.lower())
        print(f"  {path}: {errors} errors, {warnings} warnings")
        if args.strict and errors > 0:
            print(result.stdout)
            total_errors += errors
    if total_errors > 0:
        print(f"\n  total errors: {total_errors}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
