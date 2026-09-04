"""build/lock.py - SQLite advisory lock for build runner (Day 6).

Per plan section Day 6: "build/lock.py: SQLite advisory lock
(`BEGIN IMMEDIATE; ... COMMIT;`)". The lock serializes access to
shared build state across:
  - the build runner subprocess
  - HTTP handler invocations (POST /api/build/invoke)
  - daemon startup recover_orphans

Implementation: every caller opens its own connection via
db.connection.open_db() (per-thread cache, see db/connection.py),
then runs `BEGIN IMMEDIATE` to acquire the SQLite write lock.
SQLite's `BEGIN IMMEDIATE` is database-wide - there can only be
ONE writer at a time. Combined with `busy_timeout` in db.connection,
callers will block (not error) until the lock is released.

Public API:
  with build_lock(album_id):
      ... # exactly one writer holds the lock

The album_id parameter is recorded in the lock for diagnostics
(log messages on acquire/release), but SQLite's lock is global to
the database. Per-album serialization is achieved at the application
layer (queue_job uses ON CONFLICT to prevent duplicate jobs).

KNOWN LIMITATION: coroutines on the same thread that share a
per-thread connection cannot serialize via BEGIN IMMEDIATE.
Production code paths (HTTP handlers, each request on its own
thread) do not hit this. Tests that use asyncio.gather on the same
thread need to use real threads instead.

Usage example:
    from build.lock import build_lock

    def atomic_invoke(album_id, layer_id):
        with build_lock(album_id):
            job = db_build_jobs.queue_job(album_id, layer_id)
            # ... write events, mark_running, etc.
"""
from __future__ import annotations

import contextlib
import logging
import sqlite3
import threading
import time
from typing import Optional

from db.connection import open_db, close_db

_log = logging.getLogger("sonic_sounds.build.lock")

# Per-album locks are tracked here so a DEBUG-level log can show
# "stuck" locks (the holder went away). Keyed on album_id.
_active_holders: dict[str, float] = {}


@contextlib.contextmanager
def build_lock(album_id: str, *, timeout_sec: float = 30.0):
    """Acquire a SQLite advisory lock for the given album_id.

    The lock is acquired via BEGIN IMMEDIATE on the per-thread
    connection. If another thread holds the DB write lock, this
    blocks for up to `busy_timeout` (set by db.connection to 5000ms).
    We retry past that to honor `timeout_sec`.

    Yields a sqlite3.Connection. The caller MUST NOT keep it past
    the `with` block - it will be closed by close_db() on exit.

    On exit (normal or exception), commits any pending transaction
    and closes the connection.
    """
    start = time.monotonic()
    conn = open_db()
    try:
        # Drain any prior uncommitted txn on this connection.
        # Cheap: rollback() on a connection with no txn is a no-op.
        try:
            conn.execute("ROLLBACK")
        except sqlite3.OperationalError:
            pass

        deadline = start + timeout_sec
        while True:
            try:
                conn.execute("BEGIN IMMEDIATE")
                break
            except sqlite3.OperationalError as e:
                elapsed = time.monotonic() - start
                if elapsed >= timeout_sec:
                    raise TimeoutError(
                        f"could not acquire build lock for {album_id!r} "
                        f"after {timeout_sec:.1f}s (last error: {e})"
                    ) from e
                # Brief backoff and retry. SQLITE_BUSY is handled by
                # busy_timeout PRAGMA in db.connection._open_connection,
                # but SQLITE_LOCKED on the same-process case requires
                # explicit retry.
                time.sleep(0.05)
        _active_holders[album_id] = time.monotonic()
        _log.debug(f"acquired build lock for {album_id!r} (held={len(_active_holders)})")
        try:
            yield conn
        finally:
            try:
                conn.commit()  # release the write lock + commit any work
            except Exception as e:
                _log.warning(f"commit during lock release failed: {e}")
            _active_holders.pop(album_id, None)
            elapsed = time.monotonic() - start
            _log.debug(f"released build lock for {album_id!r} after {elapsed:.3f}s")
    finally:
        close_db()


def active_locks() -> dict[str, float]:
    """Snapshot of currently held locks and their acquire timestamps.

    For diagnostics: if the daemon is stuck, this lets you see which
    album is holding a lock and for how long. Returns a copy - caller
    mutations don't affect internal state.
    """
    return dict(_active_holders)


def stuck_locks(threshold_sec: float = 60.0) -> dict[str, float]:
    """Return locks held longer than `threshold_sec`.

    Used by the build runner's health check to detect abandonments
    (process crashed mid-job, lock never released).
    """
    now = time.monotonic()
    return {k: now - v for k, v in _active_holders.items() if now - v > threshold_sec}
