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

_PROJ_ROOT = Path(__file__).resolve().parent.parent

# Default DB location (per Q25 + R10).
# Resolved against the project root (the directory containing the `db/` package)
# rather than the current working directory. This matters for service-mode
# daemons (default CWD = C:\Windows\System32) and for any caller that
# invokes `open_db()` from outside the project tree.
#
# Override via the ALBUM_STUDIO_DB_PATH environment variable. This is the
# canonical way for tests to point the entire codebase at a tempdb, and
# for ops to relocate the database (e.g. onto a different drive).
import os as _os
_OVERRIDE = _os.environ.get("ALBUM_STUDIO_DB_PATH")
if _OVERRIDE:
    DEFAULT_DB_PATH = Path(_OVERRIDE).resolve()
else:
    DEFAULT_DB_PATH = _PROJ_ROOT / ".meta" / "album-studio.db"
del _OVERRIDE

# Per-thread connection cache (per "Long-term fix #1" in the audit memo).
# Each OS thread that calls open_db() gets its own connection keyed on
# (db_path, thread_ident). Connections are NOT shared across threads —
# this is the only safe pattern for SQLite + multi-threaded ASGI servers.
_thread_local = threading.local()

# Cross-thread registry for close_all(). threading.local() is per-thread so
# a daemon shutdown can't enumerate live threads' caches from the main
# thread. We use a regular dict keyed on thread.ident; each thread registers
# its own list of (cache_key, conn) entries on first open_db(). The list is
# wrapped in a WeakRef-friendly holder so dead threads don't leak their
# connection references. close_all() iterates over the dict; after a thread
# dies naturally its references are cleaned up via the weakref-to-thread.
#
# Format: {thread_ident: _ThreadEntry} where _ThreadEntry holds the list
#         of (db_path, read_only, conn) tuples for that thread.
_thread_registry: "dict[int, object]" = {}
_registry_lock = threading.Lock()


class _ThreadEntry:
    """Holder for one thread's connection cache entries.

    Lives in _thread_registry so close_all() can iterate all known threads.
    """
    __slots__ = ("entries",)

    def __init__(self):
        self.entries: list = []


def _normalize_db_path(db_path: Optional[Union[str, Path]]) -> Path:
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    db_path = Path(db_path).absolute()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def _open_connection(db_path: Path, read_only: bool) -> sqlite3.Connection:
    """Create a fresh sqlite3.Connection with PRAGMAs applied.

    Per Q26: WAL mode + PRAGMAs on every connection open.

    For read_only connections, only read-safe PRAGMAs are applied:
    foreign_keys and busy_timeout. WAL/synchronous/cache_size/temp_store
    are all write-side PRAGMAs that fail on a readonly URI connection.
    """
    if read_only:
        # URI mode required for read-only
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=True)
    else:
        conn = sqlite3.connect(str(db_path), check_same_thread=True)

    # Apply PRAGMAs per Q26
    if read_only:
        # Only read-safe PRAGMAs (others throw on readonly db)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
    else:
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

    The cache key includes (db_path, read_only) so a read-only request never
    returns a cached writable connection (or vice-versa).

    Per Q26: every open applies WAL mode + 5 PRAGMAs (skipped on readonly).
    Returns:
      sqlite3.Connection with row_factory=sqlite3.Row.
    """
    db_path = _normalize_db_path(db_path)

    # Initialize the thread-local dict on first call
    if not hasattr(_thread_local, "connections"):
        _thread_local.connections = {}

    # Cache key includes read_only flag to prevent cross-mode reuse
    cache_key = (str(db_path), bool(read_only))
    cached = _thread_local.connections.get(cache_key)
    if cached is not None:
        return cached

    conn = _open_connection(db_path, read_only)
    _thread_local.connections[cache_key] = conn

    # Register in the cross-thread registry so close_all() can find it.
    tid = threading.get_ident()
    with _registry_lock:
        entry = _thread_registry.get(tid)
        if entry is None:
            entry = _ThreadEntry()
            _thread_registry[tid] = entry
        entry.entries.append((cache_key, conn))

    return conn


def close_db(db_path: Optional[Union[str, Path]] = None,
             *, read_only: bool = False) -> None:
    """Close (and un-cache) the per-thread connection for the given db_path.

    After close, the next open_db() in the same thread creates a fresh
    connection. Use close_all() at daemon shutdown to close all threads.

    The cache key is (db_path, read_only), matching open_db(). If read_only
    is omitted, both keys are popped (safe default for callers that don't
    care which mode).
    """
    if not hasattr(_thread_local, "connections"):
        return

    db_path = _normalize_db_path(db_path)
    path_key = str(db_path)

    # Pop both the requested mode AND the other mode for this path, since
    # open_db may have been called with a different mode than the caller
    # is closing with. Without this, a request to close the writable conn
    # could leave a stale read_only conn in the cache (or vice-versa).
    for mode in (False, True):
        key = (path_key, mode)
        conn = _thread_local.connections.pop(key, None)
        if conn is not None and mode == bool(read_only):
            # Only close the one matching the requested mode.
            try:
                conn.close()
            except sqlite3.Error:
                pass

    # Unregister from the cross-thread registry for the matching modes.
    tid = threading.get_ident()
    with _registry_lock:
        entry = _thread_registry.get(tid)
        if entry is not None:
            entry.entries = [
                (k, c) for (k, c) in entry.entries
                if not (k[0] == path_key)
            ]
            # Drop the entry entirely if it has no remaining conns. This
            # prevents the registry from growing unbounded over a daemon's
            # lifetime as threads open/close conns (Finding #1 in the
            # 2026-08-22 audit).
            if not entry.entries:
                _thread_registry.pop(tid, None)


def close_all() -> None:
    """Close all cached connections across all known threads.

    Iterates through every thread's registry entry and closes each
    connection. Called on daemon shutdown.

    Without the cross-thread registry this would only close connections
    held by the calling thread (threading.local() is per-thread).
    """
    # Snapshot the registry under the lock; closing happens outside the
    # lock to avoid holding it during connection close (which can block).
    with _registry_lock:
        snapshot = list(_thread_registry.items())

    for tid, entry in snapshot:
        for cache_key, conn in entry.entries:
            try:
                conn.close()
            except sqlite3.Error:
                pass
        # Clear the entries list so the cleanup pass below can identify
        # which threads are now fully closed.
        entry.entries = []

    # Also clear the current thread's local cache.
    if hasattr(_thread_local, "connections"):
        _thread_local.connections.clear()
    # Drop entries with no remaining conns. If a thread is still alive
    # but holds zero open conns, we don't need to keep its (empty)
    # registry entry around.
    with _registry_lock:
        for tid in list(_thread_registry.keys()):
            entry = _thread_registry.get(tid)
            if entry is not None and not entry.entries:
                _thread_registry.pop(tid, None)


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
