"""e2e/run_all.py — full E2E orchestrator for sonic-sounds.

Run:
  python e2e/run_all.py

This is the entry-point a human (or CI) uses. It:
  1. Seeds a fresh tempdb with maren-sol + half-light-hours
  2. Starts the daemon on port 8793 (or SONIC_SOUNDS_E2E_PORT env var)
  3. Runs test_ui_full_ux.py (API + UX contract — no browser needed)
  4. If Playwright is installed: runs test_playwright_e2e.py
  5. If requested: runs test_browser_drive.py via the browser_exec
     harness (requires the Hermes preview pane to be open)
  6. Reports total pass/fail across all suites

Exit code 0 = all green. Non-zero = at least one surface failed.

Why this script exists: per sonic-sounds-day-ship-pattern §5, the
test pyramid has 5 layers (chrome / ux / api / db / unit). A single
runner that hits all of them gives one verdict per "session close".
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PORT = int(os.environ.get("SONIC_SOUNDS_E2E_PORT", "8793"))
HEADLESS = os.environ.get("SONIC_SOUNDS_E2E_HEADLESS", "1") == "1"


def _kill_daemons_on_port(port: int) -> None:
    """Kill any prior daemons binding the port (Windows-friendly)."""
    try:
        out = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            capture_output=True, text=True, timeout=5,
        ).stdout
    except Exception:
        return
    for line in out.splitlines():
        if f":{port}" in line and "LISTENING" in line:
            pid = line.strip().split()[-1]
            subprocess.run(["taskkill", "/F", "/PID", pid],
                           capture_output=True, timeout=5)


def main() -> int:
    _kill_daemons_on_port(PORT)

    tmpdir = tempfile.mkdtemp(prefix="sonic-sounds-e2e-")
    db = os.path.join(tmpdir, "test.db")
    lock = os.path.join(tmpdir, "test.lock")
    log = os.path.join(tmpdir, "test.log")

    env = os.environ.copy()
    env["SONIC_SOUNDS_DB_PATH"] = db
    env["SONIC_SOUNDS_LOCK_PATH"] = lock
    env["SONIC_SOUNDS_LOG_PATH"] = log
    env["SONIC_SOUNDS_E2E_BASE"] = f"http://127.0.0.1:{PORT}"
    env["PYTHONPATH"] = ""  # avoid hermes-venv contamination
    # Unset ANTHROPIC_API_KEY / OPENAI_API_KEY / MISTRAL_API_KEY etc —
    # the daemon shouldn't accidentally pick up an external LLM key.
    for k in list(env.keys()):
        if k.endswith("_API_KEY") and k != "SONIC_SOUNDS_E2E_BASE":
            env.pop(k, None)

    print("=" * 70)
    print(f"sonic-sounds · full E2E run · {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print(f"tmpdir: {tmpdir}")
    print(f"port:  {PORT}")
    print(f"headless: {HEADLESS}")

    # ─────────────────────────────────────────────
    # Setup: seed + daemon
    # ─────────────────────────────────────────────
    print("\n[setup] seeding db...")
    r = subprocess.run(
        [sys.executable, "-m", "db.seed", "--db", db, "--force"],
        capture_output=True, text=True, env=env, cwd=ROOT, timeout=60,
    )
    if r.returncode != 0:
        print(f"seed FAILED rc={r.returncode}: {r.stderr[:500]}")
        return 1
    print("  ok")

    print(f"\n[setup] starting daemon on :{PORT}...")
    daemon = subprocess.Popen(
        [sys.executable, "-m", "build.serve",
         "--host", "127.0.0.1", "--port", str(PORT),
         "--lock", lock, "--log", log],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env=env, cwd=ROOT,
    )
    print(f"  pid: {daemon.pid}")

    # Wait for the daemon to come up
    daemon_up = False
    for attempt in range(20):
        time.sleep(0.5)
        if daemon.poll() is not None:
            print(f"  daemon died early (rc={daemon.returncode})")
            break
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/health", timeout=1) as r:
                if r.status == 200:
                    print(f"  daemon ready after {(attempt + 1) * 0.5:.1f}s")
                    daemon_up = True
                    break
        except Exception:
            continue
    if not daemon_up:
        print("  daemon failed to bind to :%d" % PORT)
        daemon.terminate()
        try:
            daemon.wait(timeout=3)
        except subprocess.TimeoutExpired:
            daemon.kill()
        return 1

    # ─────────────────────────────────────────────
    # Suite 1: API + UX contract (no browser needed)
    # ─────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("[suite 1/4] e2e/test_ui_full_ux.py — API + UX contract")
    print("=" * 70)
    api_pass = False
    api_count = None
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(HERE, "test_ui_full_ux.py")],
            capture_output=True, text=True, env=env, cwd=ROOT, timeout=120,
        )
        # Parse the "TOTAL: N/N passed" line
        for line in r.stdout.splitlines():
            if line.startswith("TOTAL:"):
                api_count = line
                break
        if r.returncode == 0:
            print(f"  PASS  ({api_count})")
            api_pass = True
        else:
            print(f"  FAIL  rc={r.returncode}")
            print("  --- stdout (last 30 lines) ---")
            for line in r.stdout.splitlines()[-30:]:
                print("    " + line)
            print("  --- stderr (last 30 lines) ---")
            for line in r.stderr.splitlines()[-30:]:
                print("    " + line)
    except subprocess.TimeoutExpired:
        print("  FAIL  timeout after 120s")
    except Exception as e:
        print(f"  FAIL  exception: {type(e).__name__}: {e}")

    # Complete any active sessions before suite 3 (Playwright) so the
    # max-3 guard doesn't fire. The Playwright suite also does this
    # defensively, but doing it here too means suite 2's HTTP walkthrough
    # doesn't need to know about session-lifecycle.
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/sessions", timeout=5) as r:
            sessions = json.loads(r.read())
            active_count = 0
            for s in sessions:
                if s.get("status") == "active":
                    urllib.request.urlopen(
                        urllib.request.Request(
                            f"http://127.0.0.1:{PORT}/api/sessions/{s['id']}/complete",
                            method="POST",
                            headers={"Content-Type": "application/json"},
                        ),
                        timeout=5,
                    )
                    active_count += 1
            if active_count:
                print(f"\n[cleanup] completed {active_count} lingering active sessions before suite 3")
    except Exception as e:
        print(f"\n[cleanup] warning: could not clean up sessions: {e}")

    # ─────────────────────────────────────────────
    # Suite 2: Day 13-14 surface tests (cover, audio, guide, track_count)
    # ─────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("[suite 2/4] e2e/test_surfaces_day13.py — Day 13-14 surfaces")
    print("=" * 70)
    surf_pass = False
    surf_count = None
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(HERE, "test_surfaces_day13.py")],
            capture_output=True, text=True, env=env, cwd=ROOT, timeout=120,
        )
        for line in r.stdout.splitlines():
            if "Day 13-14 surfaces:" in line:
                surf_count = line
                break
        if r.returncode == 0:
            print(f"  PASS  ({surf_count or 'see above'})")
            surf_pass = True
        else:
            print(f"  FAIL  rc={r.returncode}")
            print("  --- stdout (last 40 lines) ---")
            for line in r.stdout.splitlines()[-40:]:
                print("    " + line)
            print("  --- stderr (last 20 lines) ---")
            for line in r.stderr.splitlines()[-20:]:
                print("    " + line)
    except subprocess.TimeoutExpired:
        print("  FAIL  timeout after 120s")
    except Exception as e:
        print(f"  FAIL  exception: {type(e).__name__}: {e}")

    # ─────────────────────────────────────────────
    # Suite 3: Playwright (if installed)
    # ─────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("[suite 3/4] e2e/test_playwright_e2e.py — Playwright sync API")
    print("=" * 70)
    pw_pass = False
    pw_count = None
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        pw_available = True
    except ImportError:
        pw_available = False
    if not pw_available:
        print("  SKIP  Playwright not installed (pip install playwright)")
    else:
        try:
            r = subprocess.run(
                [sys.executable, os.path.join(HERE, "test_playwright_e2e.py")],
                capture_output=True, text=True, env=env, cwd=ROOT, timeout=120,
            )
            for line in r.stdout.splitlines():
                if "PLAYWRIGHT E2E:" in line:
                    pw_count = line
                    break
            if r.returncode == 0:
                print(f"  PASS  ({pw_count or 'see above'})")
                pw_pass = True
            else:
                print(f"  FAIL  rc={r.returncode}")
                print("  --- stdout (last 30 lines) ---")
                for line in r.stdout.splitlines()[-30:]:
                    print("    " + line)
        except subprocess.TimeoutExpired:
            print("  FAIL  timeout after 120s")
        except Exception as e:
            print(f"  FAIL  exception: {type(e).__name__}: {e}")

    # ─────────────────────────────────────────────
    # Suite 4: JS console-error guard (Day 14)
    # ─────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("[suite 4/4] JS console-error guard — no $(...).forEach etc.")
    print("=" * 70)
    # The console-error guard is also enforced by tests/test_studio_guide.py
    # ::TestNoDollarForEachBug. Run that pytest here for completeness.
    js_pass = False
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest",
             "tests/test_studio_guide.py::TestNoDollarForEachBug",
             "-v", "--tb=short"],
            capture_output=True, text=True, env=env, cwd=ROOT, timeout=30,
        )
        if r.returncode == 0:
            js_pass = True
            print("  PASS  $(...).forEach lint guard active")
        else:
            print("  FAIL  $(...).forEach lint guard tripped:")
            for line in r.stdout.splitlines():
                if "FAIL" in line or "Error" in line or "site/" in line:
                    print("    " + line)
    except Exception as e:
        print(f"  SKIP  exception: {type(e).__name__}: {e}")

    # ─────────────────────────────────────────────
    # Teardown
    # ─────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("[teardown] stopping daemon...")
    daemon.terminate()
    try:
        daemon.wait(timeout=5)
    except subprocess.TimeoutExpired:
        daemon.kill()
    print("  done")

    # ─────────────────────────────────────────────
    # Final report
    # ─────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)
    print(f"  suite 1 (UX contract): {'PASS' if api_pass else 'FAIL'}  {api_count or ''}")
    print(f"  suite 2 (Day 13-14):   {'PASS' if surf_pass else 'FAIL'}  {surf_count or ''}")
    if pw_available:
        print(f"  suite 3 (Playwright):  {'PASS' if pw_pass else 'FAIL'}  {pw_count or ''}")
    else:
        print("  suite 3 (Playwright):  SKIP  (not installed)")
    print(f"  suite 4 (JS lint):     {'PASS' if js_pass else 'FAIL'}")

    overall = api_pass and surf_pass and js_pass and (pw_pass if pw_available else True)
    print("\n  OVERALL: " + ("PASS" if overall else "FAIL"))
    print("=" * 70)
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
