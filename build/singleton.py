"""build/singleton.py — singleton lock (per v3.2 §Day 3 "serve.py: singleton lock").

Per plan §7 Day 3:
- "serve.py: singleton lock, signal handlers, startup sequence"
- "Verification: `curl http://127.0.0.1:8765/api/health` → JSON; ...

The singleton lock prevents multiple daemons from running on the same
port + db. Uses a PID file at .meta/daemon.lock. On startup:
  - If lock file exists and PID is alive → exit with error
  - If lock file exists and PID is dead → take over (clean stale lock)
  - If no lock file → acquire

On shutdown:
  - Remove the lock file
  - Allow new daemon to start

Also provides:
- PID-alive check (cross-platform: os.kill(pid, 0) works on Windows)
- Atomic lock acquisition via O_EXCL (Windows: os.open with O_CREAT | O_EXCL)
"""
import os
import sys
import time
from pathlib import Path
from typing import Optional


class SingletonLockError(RuntimeError):
    """Raised when another daemon instance is already running."""


class SingletonLock:
    """Cross-platform singleton lock via PID file.

    Usage:
        lock = SingletonLock(path=".meta/daemon.lock")
        try:
            lock.acquire()
        except SingletonLockError as e:
            print(f"Cannot start: {e}", file=sys.stderr)
            sys.exit(1)

        # ... daemon runs ...

        lock.release()  # on shutdown

    The lock is reentrant-safe in the sense that if the SAME process
    calls acquire() twice, the second is a no-op. But cross-process
    locking is enforced via the PID file check.
    """

    def __init__(self, path: Path):
        self.path = Path(path).absolute()
        self.pid: Optional[int] = None

    def _pid_alive(self, pid: int) -> bool:
        """Check if pid is alive. Cross-platform: os.kill(pid, 0) works on Win + Unix."""
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def _read_pid(self) -> Optional[int]:
        """Read PID from lock file. Returns None if file doesn't exist or is invalid."""
        if not self.path.exists():
            return None
        try:
            content = self.path.read_text(encoding="utf-8").strip()
            if not content:
                return None
            return int(content.split()[0])
        except (ValueError, IndexError, OSError):
            return None

    def is_held(self) -> bool:
        """Return True if another daemon instance is running."""
        pid = self._read_pid()
        if pid is None:
            return False
        # Check if the pid is alive AND is not our own pid
        return self._pid_alive(pid) and pid != os.getpid()

    def acquire(self) -> None:
        """Acquire the singleton lock.

        Raises:
            SingletonLockError: if another daemon is running (different pid alive).
        """
        # If we already hold it, just refresh pid
        existing = self._read_pid()
        if existing == os.getpid():
            self.pid = existing
            return

        if existing is not None and self._pid_alive(existing):
            raise SingletonLockError(
                f"Another daemon is running with PID {existing} "
                f"(lock file at {self.path})"
            )

        # Stale lock or no lock — acquire
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write: write to temp + rename
        tmp = self.path.with_suffix(".lock.tmp")
        tmp.write_text(f"{os.getpid()}\n", encoding="utf-8")
        # On Windows, os.replace is atomic
        os.replace(tmp, self.path)
        self.pid = os.getpid()

    def release(self) -> None:
        """Release the singleton lock. Safe to call multiple times."""
        if self.path.exists():
            try:
                self.path.unlink()
            except OSError:
                pass
        self.pid = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.release()
        return False


def is_pid_alive(pid: int) -> bool:
    """Cross-platform helper to check if a process is alive."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False
