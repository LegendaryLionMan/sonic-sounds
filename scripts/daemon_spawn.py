"""scripts/daemon-spawn - low-level daemon lifecycle helper.

Wraps the daemon's start/stop with full logging and signal handling.
Used by scripts/dev.py and the e2e orchestrator.

This is intentionally minimal — it's the foundation that the dev
script and the CI script both build on. Just spawn, wait-for-health,
kill-on-failure, and tail logs.
"""
from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = Path(r"C:\Users\lion_\AppData\Local\Temp\sonic-sounds-smoke")
LOG_DIR.mkdir(parents=True, exist_ok=True)


def is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def find_daemon_pid(port: int) -> int | None:
    try:
        out = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            capture_output=True, text=True, timeout=5,
        ).stdout
    except Exception:
        return None
    for line in out.splitlines():
        if f":{port}" in line and "LISTENING" in line:
            try:
                return int(line.strip().split()[-1])
            except (ValueError, IndexError):
                continue
    return None


def kill_pid(pid: int) -> None:
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True, timeout=5,
            )
        else:
            os.kill(pid, signal.SIGTERM)
    except Exception:
        pass


def kill_port(port: int) -> bool:
    pid = find_daemon_pid(port)
    if pid is None:
        return False
    kill_pid(pid)
    for _ in range(20):
        if is_port_free(port):
            return True
        time.sleep(0.2)
    return not is_port_free(port)


def spawn(port: int, env_extra: dict | None = None) -> subprocess.Popen:
    """Spawn a daemon on `port`. Returns the Popen. Stdout/stderr go to LOG_DIR."""
    out_log = LOG_DIR / "daemon-stdout.log"
    err_log = LOG_DIR / "daemon-stderr.log"
    out_log.parent.mkdir(parents=True, exist_ok=True)
    args = [sys.executable, "-m", "build.serve",
            "--host", "127.0.0.1", "--port", str(port)]
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    if sys.platform == "win32":
        return subprocess.Popen(
            args, cwd=str(ROOT),
            stdout=open(out_log, "wb"), stderr=open(err_log, "wb"),
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
                       | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            env=env,
        )
    return subprocess.Popen(
        args, cwd=str(ROOT),
        stdout=open(out_log, "wb"), stderr=open(err_log, "wb"),
        start_new_session=True,
        env=env,
    )


def wait_healthy(port: int, timeout: float = 8.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/health", timeout=0.5
            ) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.2)
    return False
