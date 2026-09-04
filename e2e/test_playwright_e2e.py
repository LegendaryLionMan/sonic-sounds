"""e2e/test_playwright_e2e.py - Day 12 Playwright E2E wrapper.

Per plan section Day 12:
  "Playwright suite: full user journey (intake → brief → assets →
   player → finalize)"

This file wraps the same e2e as e2e/test_browser_drive.py using
Playwright instead of the browser-use harness. The point is:
  1. Standardize on Playwright for CI / portable runs.
  2. Decouple from the Hermes browser-use harness so the e2e can
     run on any machine that has Playwright installed.

Prereqs:
  - Playwright Python: pip install playwright
  - Browsers:    playwright install chromium
  - Live daemon: started by e2e/run_all.py or manually (default :8793)

Run with:
  python -m pytest e2e/test_playwright_e2e.py -v

Or directly:
  python e2e/test_playwright_e2e.py
"""
from __future__ import annotations

import os
import sys
import time
import json
import urllib.error
import urllib.request
from pathlib import Path

# Make the project root importable for the e2e module
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Default to the same port the run_all.py uses; overridable via env.
BASE = os.environ.get("SONIC_STUDIO_E2E_BASE", "http://127.0.0.1:8793")


def api(method: str, path: str, data=None, base: str = BASE):
    """Tiny urllib-based API client. Mirrors e2e/test_browser_drive.api()."""
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(
        f"{base}{path}", data=body, method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            raw = r.read().decode()
            try:
                return r.status, json.loads(raw) if raw else None
            except json.JSONDecodeError:
                return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw) if raw else None
        except json.JSONDecodeError:
            return e.code, raw


# ============================================================
# Daemon lifecycle
# ============================================================

def daemon_alive(base: str = BASE, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(f"{base}/api/health", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


# ============================================================
# Playwright UI checks
# ============================================================

def playwright_studio_checks(page, results: list):
    """Run the studio page checks (mirrors test_browser_drive.py)."""
    print("[PW] Navigating to studio...")
    page.goto(f"{BASE}/site/studio.html?session={page.context._session_id_for_tests}",
              wait_until="domcontentloaded", timeout=10000)
    page.wait_for_timeout(2000)

    checks = [
        ("9 pipeline cells", "document.querySelectorAll('.pipe-cell').length === 9"),
        ("album title rendered", "document.querySelector('#album-title')?.textContent?.includes('Half-Light')"),
        ("layer=03 from build event", "document.querySelector('#stat-layer')?.textContent === '03'"),
        ("03 active", "Array.from(document.querySelectorAll('.pipe-cell.active')).some(c => c.querySelector('.pipe-cell-num')?.textContent === '03')"),
        ("10 track rows", "document.querySelectorAll('.track-row').length === 10"),
        ("track duration 3:24", "document.querySelector('.track-row .t-meta')?.textContent === '3:24'"),
    ]
    for name, expr in checks:
        try:
            ok = page.evaluate(f"() => {expr}")
        except Exception as e:
            ok = False
        results.append((name, bool(ok), "" if ok else f"eval failed: {expr}"))


def playwright_albums_checks(page, results: list):
    """Albums page checks (mirrors test_browser_drive.py)."""
    print("[PW] Navigating to albums...")
    page.goto(f"{BASE}/site/albums.html",
              wait_until="domcontentloaded", timeout=10000)
    page.wait_for_timeout(2000)
    expr = "document.querySelectorAll('.album-card').length"
    try:
        count = page.evaluate(f"() => {expr}")
        results.append(("albums.html renders album cards", count > 0, f"got {count}"))
    except Exception as e:
        results.append(("albums.html renders album cards", False, str(e)))


# ============================================================
# API contract checks (no browser required)
# ============================================================

def api_contract_checks(results: list):
    """Pure-HTTP checks against a live daemon."""
    # Health
    code, body = api("GET", "/api/health")
    results.append(("health 200", code == 200, f"got {code}"))
    if isinstance(body, dict) and "subsystems" in body:
        results.append(("build_runner subsystem = ok",
                        body["subsystems"].get("build_runner") == "ok", f"got {body['subsystems']!r}"))
        results.append(("sweepers subsystem = ok",
                        body["subsystems"].get("sweepers") == "ok", f"got {body['subsystems']!r}"))

    # Session lifecycle
    code, sess = api("POST", "/api/sessions", {"album_id": "half-light-hours"})
    sid = (sess or {}).get("id") if isinstance(sess, dict) else None
    results.append(("session create 201", code == 201, f"got {code}"))

    if sid:
        for action, expect in [("pause", "paused"), ("resume", "active"),
                                ("complete", "done")]:
            code, b = api("POST", f"/api/sessions/{sid}/{action}")
            results.append((f"session {action}",
                            isinstance(b, dict) and b.get("status") == expect,
                            f"got {code} {b}"))

    # Decisions
    if sid:
        code, d1 = api("POST", "/api/decisions", {
            "code": "M01", "tier": "mandatory", "answer": "Half-Light Hours",
            "album_id": "half-light-hours", "session_id": sid,
        })
        results.append(("decision 201", code == 201, f"got {code}"))
        results.append(("decision locked_at set",
                        isinstance(d1, dict) and d1.get("locked_at") is not None))
        if isinstance(d1, dict) and "id" in d1:
            api("DELETE", f"/api/decisions/{d1['id']}")


# ============================================================
# Main entry
# ============================================================

def run() -> int:
    if not daemon_alive():
        print(f"ERROR: daemon not reachable at {BASE}. Start it first:")
        print(f"  python -m db.seed --db /tmp/test.db --force")
        print(f"  python -m build.serve --port 8793")
        return 1

    results = []
    api_contract_checks(results)

    # Playwright (only if available)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not installed; skipping browser checks.")
        return _report(results)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Get a real session id from the daemon.
        # If there are already 3 active sessions (max limit), the
        # POST returns 409. The prior suites (test_ui_full_ux +
        # test_surfaces_day13) may leave sessions open, so complete
        # ALL active sessions here — we always need a fresh slot.
        existing_code, existing_body = api("GET", "/api/sessions")
        existing_list = (existing_body or []) if isinstance(existing_body, list) else []
        for es in existing_list:
            if isinstance(es, dict) and es.get("status") == "active":
                api("POST", f"/api/sessions/{es['id']}/complete")

        code, sess = api("POST", "/api/sessions", {"album_id": "half-light-hours"})
        sid = (sess or {}).get("id") if isinstance(sess, dict) else None
        # Post a build event so the studio can derive layer=03 from the
        # event stream (this is the same pattern the Day 7 e2e uses).
        if sid:
            api("POST", "/api/events", {
                "session_id": sid, "role": "assistant", "kind": "build",
                "content": "build", "album_id": "half-light-hours",
                "payload": {"layer": 3, "phase": "lyrics_finalize"},
            })
            page.context._session_id_for_tests = sid  # used by playwright_studio_checks
            playwright_studio_checks(page, results)
        playwright_albums_checks(page, results)

        context.close()
        browser.close()

    return _report(results)


def _report(results: list) -> int:
    def _ok(r):
        return bool(r[1]) if len(r) >= 2 else False
    passed = sum(1 for r in results if _ok(r))
    total = len(results)
    print(f"\n{'=' * 64}")
    print(f"PLAYWRIGHT E2E: {passed}/{total} passed")
    print(f"{'=' * 64}")
    for r in results:
        # Normalize to (name, ok, detail) — older code added 2-tuples.
        if len(r) == 2:
            name, ok = r
            detail = ""
        else:
            name, ok, detail = r
        mark = "✅" if ok else "❌"
        line = f"  {mark} {name}"
        if not ok and detail:
            line += f"  ({detail})"
        print(line)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(run())
