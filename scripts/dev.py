"""scripts/dev - single-command daemon launcher with auto-port handling.

Usage:
    python scripts/dev                # start daemon (defaults to :8765)
    python scripts/dev --port 9000   # start on different port
    python scripts/dev --stop        # stop any running daemon
    python scripts/dev --status       # check if daemon is up
    python scripts/dev --restart      # stop + start

This script consolidates the "find the daemon, kill it, restart it"
workflow into a single command so you don't have to remember
`Get-NetTCPConnection | kill -PID | Start-Process`.

Auto-port: if the requested port is busy, scans for the next free one
and reports it (useful when 8765 is held by an old session).
"""
from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def find_daemon_pid(port: int) -> int | None:
    """Find the python PID holding :port using netstat. Returns None on miss."""
    try:
        out = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, timeout=5,
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


def kill_pid(pid: int) -> bool:
    """Best-effort cross-platform PID kill."""
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True, timeout=5,
            )
        else:
            os.kill(pid, 15)
        return True
    except Exception:
        return False


def daemon_health(port: int, timeout: float = 1.5) -> dict:
    """Probe the daemon's /api/health and return the parsed JSON."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health",
                                     timeout=timeout) as r:
            import json
            return json.loads(r.read())
    except Exception as e:
        return {"status": "down", "error": str(e)}


def wait_for_health(port: int, timeout: float = 8.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        h = daemon_health(port, timeout=0.5)
        if h.get("status") == "ok":
            return True
        time.sleep(0.3)
    return False


def start_daemon(port: int) -> int:
    """Spawn the daemon. Returns the actual port used."""
    actual_port = port
    if not is_port_free(port):
        # Scan forward for the next free port (max 20 tries)
        for delta in range(1, 21):
            candidate = port + delta
            if is_port_free(candidate):
                actual_port = candidate
                print(f"[dev] port {port} busy, using {actual_port}")
                break
        else:
            print(f"[dev] no free port in {port}..{port+20}")
            return 1

    log_path = Path(r"C:\Users\lion_\AppData\Local\Temp\sonic-sounds-smoke\daemon-stdout.log")
    err_path = log_path.with_suffix(".err.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("")
    err_path.write_text("")

    args = [
        sys.executable, "-m", "build.serve",
        "--host", "127.0.0.1", "--port", str(actual_port),
    ]
    print(f"[dev] spawning: {' '.join(args)}")
    print(f"[dev] cwd: {ROOT}")
    print(f"[dev] stdout: {log_path}")
    print(f"[dev] stderr: {err_path}")

    if sys.platform == "win32":
        proc = subprocess.Popen(
            args,
            cwd=str(ROOT),
            stdout=open(log_path, "wb"),
            stderr=open(err_path, "wb"),
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
    else:
        proc = subprocess.Popen(
            args,
            cwd=str(ROOT),
            stdout=open(log_path, "wb"),
            stderr=open(err_path, "wb"),
            start_new_session=True,
        )
    print(f"[dev] pid: {proc.pid}")

    if wait_for_health(actual_port):
        print(f"[dev] daemon ready on http://127.0.0.1:{actual_port}")
        print(f"[dev] health: {daemon_health(actual_port, timeout=1.0)}")
    else:
        print(f"[dev] daemon didn't come up within 8s — see {err_path}")
        return 2

    return 0


def stop_daemon(port: int) -> int:
    pid = find_daemon_pid(port)
    if pid is None:
        print(f"[dev] no daemon on :{port}")
        return 0
    print(f"[dev] killing pid {pid} on :{port}")
    if kill_pid(pid):
        # Wait for port to free
        for _ in range(20):
            if is_port_free(port):
                print(f"[dev] port :{port} freed")
                return 0
            time.sleep(0.2)
        print(f"[dev] port :{port} still busy after kill")
        return 1
    print(f"[dev] kill failed")
    return 1


def main() -> int:
    p = argparse.ArgumentParser(description="sonic-sounds dev daemon launcher")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--stop", action="store_true")
    p.add_argument("--status", action="store_true")
    p.add_argument("--restart", action="store_true")
    args = p.parse_args()

    if args.stop:
        return stop_daemon(args.port)
    if args.restart:
        stop_daemon(args.port)
        time.sleep(0.5)
        return start_daemon(args.port)
    if args.status:
        pid = find_daemon_pid(args.port)
        h = daemon_health(args.port, timeout=1.0)
        print(f"port :{args.port}  pid: {pid}  status: {h.get('status')}")
        if "counts" in h:
            print(f"  counts: {h['counts']}")
        return 0
    return start_daemon(args.port)


if __name__ == "__main__":
    sys.exit(main())
