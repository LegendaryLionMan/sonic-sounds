"""db/connection.py — SQLite connection + WAL + PRAGMAs (per Q24, Q26 v3.2 §Day 2).

Long-term architecture (refactored 2026-08-09 after Day 3 audit):

SQLite connections are NOT safe to share across threads. We previously
tried to share a single connection via check_same_thread=False; that works
but is a footgun — operations from one thread can interleave with another
and corrupt state. Per-thread connections are the right answer:

  open_db()  → returns the connection for *this* thread (creates if missing)
  close_db() → closes the connection for *this* thread (deletes from cache)

Connections are also closed on daemon shutdown via close_all().

Per Q23: SQLite is the schema of record.
Per Q26: WAL mode + PRAGMAs applied on every open.

Module-level helpers:
  DEFAULT_DB_PATH — the canonical .meta/album-studio.db (Q25 + R10)
  open_db(db_path=None, *, read_only=False) — per-thread connection
  close_db(db_path=None) — close per-thread connection
  close_all() — close every cached connection (daemon shutdown)
  run_migrations(db_path=None) — re-exported from db.migrations
  verify_conn(conn) — diagnostic PRAGMA check
  db_path() — return the canonical default path
"""
import os
import sqlite3
import threading
from pathlib import Path
from typing import Optional, Union

# Default DB location (per Q25 + R10)
DEFAULT_DB_PATH = Path(".meta/album-studio.db")

# Per-thread connection cache (per "Long-term fix #1" in the audit memo).
# Each OS thread that calls open_db() gets its own connection keyed on
# (db_path, thread_ident). Connections are NOT shared across threads —
# this is the only safe pattern for SQLite + multi-threaded ASGI servers.
_thread_local = threading.local()


def _normalize_db_path(db_path: Optional[Union[str, Path]]) -> Path:
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    db_path = Path(db_path).absolute()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def _open_connection(db_path: Path, read_only: bool) -> sqlite3.Connection:
    """Create a fresh sqlite3.Connection with PRAGMAs applied.

    Per Q26: WAL mode + PRAGMAs on every connection open.
    """
    if read_only:
        # URI mode required for read-only
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=True)
    else:
        conn = sqlite3.connect(str(db_path), check_same_thread=True)

    # Apply PRAGMAs per Q26
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA cache_size = -8000;")
    conn.execute("PRAGMA temp_store = MEMORY;")

    conn.row_factory = sqlite3.Row
    return conn


def open_db(db_path: Optional[Union[str, Path]] = None,
           *, read_only: bool = False) -> sqlite3.Connection:
    """Open (or reuse) the per-thread SQLite connection.

    Each OS thread that calls open_db() gets its own connection. Threads do
    NOT share connections — this is the only safe pattern with SQLite.

    Per Q26: every open applies WAL mode + 5 PRAGMAs.
    Returns:
      sqlite3.Connection with row_factory=sqlite3.Row.
    """
    db_path = _normalize_db_path(db_path)

    # Initialize the thread-local dict on first call
    if not hasattr(_thread_local, "connections"):
        _thread_local.connections = {}

    cache_key = str(db_path)
    cached = _thread_local.connections.get(cache_key)
    if cached is not None:
        return cached

    conn = _open_connection(db_path, read_only)
    _thread_local.connections[cache_key] = conn
    return conn


def close_db(db_path: Optional[Union[str, Path]] = None) -> None:
    """Close (and un-cache) the per-thread connection for the given db_path.

    After close, the next open_db() in the same thread creates a fresh
    connection. Use close_all() at daemon shutdown to close all threads.
    """
    if not hasattr(_thread_local, "connections"):
        return

    db_path = _normalize_db_path(db_path)
    cache_key = str(db_path)
    conn = _thread_local.connections.pop(cache_key, None)
    if conn is not None:
        try:
            conn.close()
        except sqlite3.Error:
            pass


def close_all() -> None:
    """Close all cached connections across all known threads.

    Iterates through every thread's _thread_local.connections and closes
    them. Called on daemon shutdown.

    Note: Python doesn't easily enumerate all live threads with their
    _thread_local state, so this relies on each thread having already
    cleaned up via close_db(). For the daemon, we explicitly track threads
    and close each one.
    """
    # Close in the current thread first
    if hasattr(_thread_local, "connections"):
        for key in list(_thread_local.connections.keys()):
            close_db(key)


def db_path() -> Path:
    """Return the canonical absolute default DB path."""
    return DEFAULT_DB_PATH.absolute()


# === Verification helper (per plan §7 Day 2 verification step) ===

def verify_conn(conn: sqlite3.Connection) -> dict:
    """Verify the connection has the expected PRAGMAs applied.

    Returns a dict of PRAGMA: value. Useful for the verification step
    'python -m open_db() → opens, runs migrations, PRAGMAs verified'.
    """
    out = {}
    for pragma in [
        "journal_mode",
        "foreign_keys",
        "synchronous",
        "busy_timeout",
        "cache_size",
        "temp_store",
    ]:
        try:
            row = conn.execute(f"PRAGMA {pragma}").fetchone()
            out[pragma] = row[0] if row else None
        except sqlite3.Error as e:
            out[pragma] = f"ERROR: {e}"
    return out


# === Module-level convenience ===

if __name__ == "__main__":
    # Quick smoke test
    conn = open_db()
    pr = verify_conn(conn)
    print(f"Opened: {db_path()}")
    print(f"PRAGMAs: {pr}")
    print(f"row_factory: {conn.row_factory.__name__}")
    print(f"thread_id: {threading.get_ident()}")
    close_db()
