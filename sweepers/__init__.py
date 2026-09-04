"""sweepers/__init__.py — Day 8 sweeper registry and scheduler.

The 5 sweepers per plan section Day 8:
  - idle_pause: every 5 min, pause active sessions idle for 12h+
  - wal_checkpoint: every 15 min, PRAGMA wal_checkpoint(TRUNCATE)
  - quota: every 5 min, snapshot mmx quota via MCP or CLI
  - mirror: every hour, walk albums/ → OneDrive
  - log_rotate: every 5 min (or per-write), check size + rotate at 10MB

The daemon registers a daemon thread per sweeper. Each thread runs an
infinite loop with a sleep interval and catches all exceptions so one
broken sweeper can't crash the daemon.

Thread lifecycle:
  start()  - spawn all 5 daemon threads, return list of Thread objects
  stop()   - signal all to exit and join (for clean shutdown)
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

_log = logging.getLogger("sonic_studio.sweepers")

# Sweeper intervals in seconds (per plan)
INTERVALS = {
    "idle_pause": 5 * 60,        # 5 min
    "wal_checkpoint": 15 * 60,   # 15 min
    "quota": 5 * 60,             # 5 min
    "mirror": 60 * 60,           # 1 hour
    "log_rotate": 5 * 60,        # 5 min
}


class _StopEvent:
    """Thread-safe stop signal. Daemon threads poll this."""
    def __init__(self):
        self._flag = threading.Event()
    def set(self):
        self._flag.set()
    def is_set(self) -> bool:
        return self._flag.is_set()


def _make_loop(name: str, interval_sec: int, fn: Callable[[], dict],
              stop: _StopEvent, run_once_at_start: bool = False) -> None:
    """Thread body for a sweeper. Runs fn() every interval_sec until stopped.

    Catches all exceptions so one broken sweeper can't kill the daemon.
    Logs each invocation's outcome at INFO level.
    """
    if run_once_at_start:
        _invoke(name, fn)
    while not stop.is_set():
        # Use Event.wait so stop signal is responsive (no full sleep)
        if stop._flag.wait(timeout=interval_sec):
            break  # stop signalled
        _invoke(name, fn)


def _invoke(name: str, fn: Callable[[], dict]) -> None:
    try:
        result = fn()
        if isinstance(result, dict):
            # Compact log: highlight errors
            errs = result.get("errors") or []
            extra = f" errors={len(errs)}" if errs else ""
            _log.info(f"sweep[{name}] ok={result.get('ok', '?')}{extra}")
        else:
            _log.info(f"sweep[{name}] returned {result!r}")
    except Exception as e:
        _log.exception(f"sweep[{name}] crashed: {e}")


def start_all(stop_event: Optional[_StopEvent] = None) -> tuple[list[threading.Thread], _StopEvent]:
    """Spawn one daemon thread per registered sweeper.

    Args:
      stop_event: shared stop signal. If None, a new _StopEvent is
        created (and returned so caller can stop later).

    Returns:
      (threads, stop_event). Caller should hold onto both; pass to
      stop_all() when daemon is shutting down.
    """
    from sweepers import idle_pause, wal_checkpoint, quota, mirror, log_rotate

    if stop_event is None:
        stop_event = _StopEvent()

    sweepers = [
        ("idle_pause",    INTERVALS["idle_pause"],    idle_pause.run_sweep,    False),
        ("wal_checkpoint", INTERVALS["wal_checkpoint"], wal_checkpoint.run_sweep, False),
        ("quota",         INTERVALS["quota"],         quota.run_sweep,         False),
        ("mirror",        INTERVALS["mirror"],        mirror.run_sweep,        False),
        ("log_rotate",    INTERVALS["log_rotate"],    log_rotate.run_sweep,    False),
    ]
    threads: list[threading.Thread] = []
    for name, interval, fn, run_first in sweepers:
        t = threading.Thread(
            target=_make_loop,
            args=(name, interval, fn, stop_event, run_first),
            daemon=True,
            name=f"sweeper-{name}",
        )
        t.start()
        threads.append(t)
        _log.info(f"started sweeper[{name}] every {interval}s")
    return threads, stop_event


def stop_all(threads: list[threading.Thread], stop_event: _StopEvent,
             timeout: float = 5.0) -> None:
    """Signal all sweeper threads to exit and join them."""
    stop_event.set()
    for t in threads:
        t.join(timeout=timeout)
        if t.is_alive():
            _log.warning(f"sweeper thread {t.name} did not exit within {timeout}s")
