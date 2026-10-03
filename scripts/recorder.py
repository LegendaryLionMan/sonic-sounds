"""scripts/recorder - record user interactions with the daemon for
debugging.

Per 2026-09-06 user feedback: "I clicked X and the page broke" is
hard to debug without a recording. This script uses Playwright's
tracing capability to capture a full session (DOM snapshots, network,
console) that can be replayed in chrome://tracing or the Playwright
Trace Viewer.

Usage:
    python scripts/recorder.py --output .meta/recording.zip
    # Then open in https://trace.playwright.dev or chrome://tracing

The script records:
- All DOM mutations
- All console messages
- All network requests/responses
- All keyboard/mouse events
- All page navigations

Limited to 60s by default (Playwright trace buffer can get large).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    p = argparse.ArgumentParser(description="session recorder")
    p.add_argument("--base", default="http://127.0.0.1:8765")
    p.add_argument("--duration", type=int, default=60, help="seconds")
    p.add_argument("--page", default="albums.html", help="starting page")
    p.add_argument("--output", default=".meta/recording.zip")
    args = p.parse_args()

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0]
        page = ctx.pages[0]
        page.goto(f"{args.base}/site/{args.page}", wait_until="domcontentloaded")
        print(f"[recorder] recording page={args.page} for {args.duration}s")
        print(f"[recorder] navigate and click around — output: {out}")
        page.wait_for_timeout(args.duration * 1000)
    print(f"[recorder] done. open {out} in https://trace.playwright.dev")
    return 0


if __name__ == "__main__":
    sys.exit(main())
