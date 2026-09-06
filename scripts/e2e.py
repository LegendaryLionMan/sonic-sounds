"""scripts/e2e - one-shot E2E orchestrator for local dev.

Wraps e2e/test_advanced.py with daemon lifecycle management. Same
pattern as e2e/run_all.py but tailored for the advanced 10-suite +
E2E-only suite (skips Playwright suites if Playwright is unavailable).

Usage:
    python scripts/e2e                   # run against live daemon
    python scripts/e2e --spawn          # spawn daemon on a free port, then run
    python scripts/e2e --stop-after     # stop the daemon at the end
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = HERE
sys.path.insert(0, str(SCRIPTS))

from daemon_spawn import (  # type: ignore
    is_port_free, spawn, wait_healthy, kill_port, find_daemon_pid,
)

DEFAULT_PORT = 8765


def _daemon_up(port: int) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/health", timeout=1.5
        ) as r:
            return r.status == 200
    except Exception:
        return False


def main() -> int:
    p = argparse.ArgumentParser(description="run E2E advanced suite")
    p.add_argument("--base", type=str, default=None,
                   help="daemon base URL (default: live :8765)")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--spawn", action="store_true",
                   help="spawn a fresh daemon on a free port")
    p.add_argument("--stop-after", action="store_true",
                   help="stop the spawned daemon after the run")
    args = p.parse_args()

    spawned = False
    port = args.port

    if args.spawn:
        # Find a free port
        for delta in range(0, 21):
            if is_port_free(port + delta):
                port = port + delta
                break
        print(f"[e2e] spawning daemon on :{port}")
        spawn(port)
        spawned = True
        if not wait_healthy(port, timeout=8):
            print("[e2e] daemon didn't come up")
            return 2
    else:
        # Use live daemon; verify
        if not _daemon_up(port):
            print(f"[e2e] no daemon on :{port}; pass --spawn to start one")
            return 2

    env = os.environ.copy()
    env["SONIC_SOUNDS_E2E_BASE"] = args.base or f"http://127.0.0.1:{port}"

    try:
        r = subprocess.run(
            [sys.executable, str(ROOT / "e2e" / "test_advanced.py")],
            env=env, cwd=str(ROOT), timeout=900,
        )
        return r.returncode
    finally:
        if spawned and args.stop_after:
            print(f"[e2e] stopping daemon on :{port}")
            kill_port(port)


if __name__ == "__main__":
    sys.exit(main())
