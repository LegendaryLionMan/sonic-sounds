"""tools/ui_smoke.py — single-shot Playwright UI smoke for the album-studio preview.

The reason this exists: every UI change in album-studio needs to be verified
in a real browser, not via HTTP-only probes. We had three failures:

  1. browser_exec MCP kept timing out (Chrome profile lock issues, ~420s each)
  2. `chrome --headless --dump-dom` returns 0 bytes on Windows (known bug)
  3. `chrome --headless --remote-debugging-port` rejects WS upgrades
     with HTTP 500 ("server rejected WebSocket connection") on Chrome 152
     even with `--remote-allow-origins=*`

What works: Playwright Python's `chromium_headless_shell` (the bundled
minimal headless chrome that ships with `playwright install`). Located at
`~/AppData/Local/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-win64/chrome-headless-shell.exe`.

Usage (from project root or anywhere — paths are absolute):

  python tools/ui_smoke.py
  python tools/ui_smoke.py --url http://127.0.0.1:8765/site/library.html
  python tools/ui_smoke.py --url ... --out C:\\shots\\foo.png --no-screenshot

Exit codes:
  0  = all asserts passed + screenshots saved
  1  = any assertion failed (DOM missing, click didn't fire, etc.)
  2  = infra (daemon not up, chrome binary missing, websockets lib missing)

Default assertion suite targets the library-page album player. Override with
--asserts none for pure screenshot mode.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Hermes venv python sits next to this script. Import Playwright lazily.
HERMES_PY = Path(r"C:/Users/lion_/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe")

# Playwright bundled headless chromium (no system Chrome required, no MCP needed)
CHROME_BIN = Path(
    r"C:/Users/lion_/AppData/Local/ms-playwright"
    r"/chromium_headless_shell-1234/chrome-headless-shell-win64/chrome-headless-shell.exe"
)

# Default target
DEFAULT_URL = "http://127.0.0.1:8765/site/library.html"
DEFAULT_OUT_DIR = Path(r"C:/Users/lion_/AppData/Local/Temp/album-studio-smoke")


def _chrome_ready() -> tuple[bool, str]:
    if not CHROME_BIN.exists():
        # Fallback: glob for any chromium_headless_shell-* version
        import glob
        cands = sorted(glob.glob(
            r"C:/Users/lion_/AppData/Local/ms-playwright/chromium_headless_shell-*"
            r"/chrome-headless-shell-win64/chrome-headless-shell.exe"
        ))
        if cands:
            return True, f"fallback-chromium:{cands[-1]}"
        return False, f"chrome binary not found at {CHROME_BIN}"
    return True, str(CHROME_BIN)


def _daemon_up(url: str) -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return 200 <= r.status < 400
    except Exception:
        return False


DEFAULT_ASSERTS = [
    # (id, css selector, label)
    ("player mount",   "#library-player-mount",       "library.html slot present"),
    ("player shell",   ".lib-player",                  "player shell rendered"),
    ("first track",    ".lib-track[data-track-i='0']", "first track row present"),
    ("last track",     ".lib-track[data-track-i='9']", "10 tracks rendered"),
    ("audio element",  "#lib-audio",                   "<audio> element for playback"),
    ("seek slider",    ".lib-seek",                    "seek bar"),
    ("volume slider",  ".lib-vol",                     "volume bar"),
    ("play/pause",     ".lib-playpause",               "play/pause button"),
]


def run(args: argparse.Namespace) -> int:
    # Pre-flight
    ok, info = _chrome_ready()
    if not ok:
        print(f"[ui-smoke] FAIL: {info}", file=sys.stderr)
        return 2
    if not _daemon_up(args.url):
        print(f"[ui-smoke] FAIL: daemon at {args.url} not responding", file=sys.stderr)
        return 2

    if not args.quiet:
        print(f"[ui-smoke] chrome: {info}")
        print(f"[ui-smoke] target: {args.url}")

    # Lazy import Playwright (so import errors don't break --help)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        print(f"[ui-smoke] FAIL: playwright not installed: {e}", file=sys.stderr)
        return 2

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    fails: list[str] = []
    assertions_run = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=info if info.startswith("fallback-chromium:") else str(CHROME_BIN),
            headless=True,
            args=["--no-sandbox", "--disable-gpu"],
        )
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        page.goto(args.url, wait_until="networkidle", timeout=20000)
        # Wait for player mount specifically (this is the slow one — JS needs to fetch /api/albums + tracks)
        if not args.no_asserts and args.asserts == "default":
            try:
                page.wait_for_selector(".lib-player", timeout=10000)
            except Exception as e:
                fails.append(f"player never mounted: {e}")

        # Run asserts
        if not args.no_asserts and args.asserts == "default":
            for label, selector, desc in DEFAULT_ASSERTS:
                assertions_run += 1
                try:
                    found = page.query_selector(selector)
                except Exception as e:
                    found = None
                    fails.append(f"{label} ({desc}): query failed: {e}")
                if not found:
                    fails.append(f"{label} ({desc}): selector '{selector}' not found")
                else:
                    if not args.quiet:
                        print(f"  PASS  {label:18s}  {selector}")

        # Track playback smoke (only when on library page)
        if "library.html" in args.url and not args.no_asserts:
            try:
                page.click(".lib-track[data-track-i='0']")
                page.wait_for_timeout(700)
                src = page.evaluate("(document.querySelector('#lib-audio') || {}).src || null")
                paused = page.evaluate("(document.querySelector('#lib-audio') || {}).paused")
                cur = page.evaluate("(document.querySelector('#lib-audio') || {}).currentTime || 0")
                assertions_run += 4
                if not src or "/api/audio/" not in src:
                    fails.append(f"audio.src missing: got {src!r}")
                if paused:
                    fails.append(f"audio.paused is True after click (should be playing)")
                if cur <= 0:
                    fails.append(f"audio.currentTime={cur} after click (should advance)")
                if not args.quiet:
                    print(f"  PASS  audio.src          {src}")
                    print(f"  PASS  audio.paused       {paused}")
                    print(f"  PASS  audio.currentTime  {cur:.2f}s")
            except Exception as e:
                fails.append(f"playback smoke failed: {e}")

        # Screenshots
        if not args.no_screenshot:
            idle_shot = out / f"{args.name}-idle.png"
            playing_shot = out / f"{args.name}-playing.png"
            page.screenshot(path=str(idle_shot), full_page=False)
            print(f"\n[ui-smoke] idle screenshot: {os.path.getsize(idle_shot)} bytes -> {idle_shot}")
            if "library.html" in args.url:
                # Re-screenshot during play for visual diff
                page.click(".lib-track[data-track-i='0']")
                page.wait_for_timeout(500)
                page.screenshot(path=str(playing_shot), full_page=False)
                print(f"[ui-smoke] playing screenshot: {os.path.getsize(playing_shot)} bytes -> {playing_shot}")

        browser.close()

    # Report
    print(f"\n=== ui-smoke === {assertions_run - len(fails)}/{assertions_run} asserts passed, "
          f"{len(fails)} failed")
    if fails:
        print("\nFAILURES:")
        for f in fails:
            print(f"  - {f}")
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Single-shot Playwright UI smoke for album-studio")
    ap.add_argument("--url", default=DEFAULT_URL, help="Target URL (default: library.html)")
    ap.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="Output directory")
    ap.add_argument("--name", default="library", help="Screenshot filename prefix")
    ap.add_argument("--no-screenshot", action="store_true", help="Skip screenshots (asserts only)")
    ap.add_argument("--no-asserts", action="store_true", help="Skip DOM asserts (screenshot only)")
    ap.add_argument("--asserts", default="default", choices=["default", "none"],
                    help="Assert suite to run")
    ap.add_argument("--quiet", action="store_true", help="Less output")
    args = ap.parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
