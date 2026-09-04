"""scripts/ensure_preview_daemon.py — guarantee album-studio preview is up.

Idempotent, polling-only. Called by the hermes cron grid every 5 minutes.
Workflow:
  1. Probe GET http://127.0.0.1:8765/api/health with 3s timeout.
  2. Healthy → exit 0 silently (no output).
  3. Down → spawn the daemon via Python subprocess, write PID file.
  4. Wait up to 10s for /api/health to return 200.
  5. If still down → exit 1 with stderr detail.

The script owns NOTHING about content — daemon is what serves content.
This is purely a process-supervisor for the preview.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON = Path(os.environ.get("HERMES_VENV_PYTHON", r"C:\Users\lion_\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"))
HOST = "127.0.0.1"
PORT = 8765
PID_FILE = PROJECT_ROOT / ".meta" / "preview_daemon.pid"
LOG_FILE = PROJECT_ROOT / ".meta" / "preview_daemon.log"
LOCK_FILE = PROJECT_ROOT / ".meta" / "daemon.lock"
HEALTH_URL = f"http://{HOST}:{PORT}/api/health"


def is_healthy(timeout: float = 3.0) -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=timeout) as r:
            return r.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError, ConnectionError, TimeoutError, OSError):
        return False


def is_daemon_running() -> bool:
    """True if PID file exists and the PID is alive, OR port 8765 is listening."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if h:
                try:
                    code = ctypes.c_ulong()
                    ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
                    if code.value == STILL_ACTIVE:
                        return True
                finally:
                    ctypes.windll.kernel32.CloseHandle(h)
        except (ValueError, OSError):
            pass
    # Fall back to port check
    return is_healthy(timeout=1.0)


def spawn_daemon() -> int:
    """Start the daemon as a detached subprocess. Returns the new PID."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Open log file for append
    logf = open(LOG_FILE, "ab", buffering=0)
    proc = subprocess.Popen(
        [str(PYTHON), "-m", "build.serve", "--host", HOST, "--port", str(PORT)],
        cwd=str(PROJECT_ROOT),
        stdout=logf,
        stderr=logf,
        stdin=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
        close_fds=True,
    )
    PID_FILE.write_text(str(proc.pid))
    return proc.pid


def wait_for_healthy(max_wait: float = 10.0) -> bool:
    deadline = time.monotonic() + max_wait
    while time.monotonic() < deadline:
        if is_healthy(timeout=1.5):
            return True
        time.sleep(0.5)
    return False


def main() -> int:
    if is_daemon_running():
        # Healthy — silent success so cron output stays quiet.
        return 0

    # Daemon not running. Try to spawn.
    sys.stderr.write(f"[ensure_preview_daemon] daemon not healthy on {HEALTH_URL}, spawning...\n")
    try:
        pid = spawn_daemon()
    except Exception as e:
        sys.stderr.write(f"[ensure_preview_daemon] spawn failed: {type(e).__name__}: {e}\n")
        return 1
    sys.stderr.write(f"[ensure_preview_daemon] spawned PID {pid}, waiting for healthy...\n")

    if wait_for_healthy(max_wait=12.0):
        sys.stderr.write(f"[ensure_preview_daemon] healthy after spawn (PID {pid})\n")
        return 0

    sys.stderr.write(f"[ensure_preview_daemon] spawned PID {pid} but never became healthy in 12s\n")
    sys.stderr.write(f"[ensure_preview_daemon] tail of {LOG_FILE.name}:\n")
    try:
        tail = LOG_FILE.read_text(errors="replace").splitlines()[-20:]
        sys.stderr.write("\n".join(tail) + "\n")
    except Exception as e:
        sys.stderr.write(f"  (could not read log: {e})\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
