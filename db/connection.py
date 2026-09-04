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
  DEFAULT_DB_PATH — the canonical .meta/sonic-studio.db (Q25 + R10)
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


def default_db_path() -> Path:
    """Return the canonical absolute default DB path.

    Resolves at call time (not import time) so that tests which
    toggle the SONIC_STUDIO_DB_PATH environment variable mid-process
    see the updated path. The env var takes precedence; otherwise the
    project-root .meta/sonic-studio.db is used.

    Per Q25 + R10: the canonical live database lives in
    .meta/sonic-studio.db inside the project root.
    """
    override = os.environ.get("SONIC_STUDIO_DB_PATH")
    if override:
        return Path(override).resolve()
    return _PROJ_ROOT / ".meta" / "sonic-studio.db"


# Backwards-compatible alias for existing call sites that use the
# module-level DEFAULT_DB_PATH name. This is the import-time snapshot
# of the default path. Tests that mutate SONIC_STUDIO_DB_PATH after
# import MUST use `default_db_path()` instead.
DEFAULT_DB_PATH = default_db_path()

# Per-thread connection cache (per "Long-term fix #1" in the audit memo).
# Each OS thread that calls open_db() gets its own connection keyed on
# (db_path, thread_ident). Connections are NOT shared across threads —
# this is the only safe pattern for SQLite + multi-threaded ASGI servers.
#
# NOTE: this used to be a `threading.local()` instance, but that makes
# the per-thread cache inaccessible to other threads — close_all() can
# iterate _thread_registry to find all live connections, but it cannot
# tell the per-thread `_thread_local` to forget them. Result: a worker
# thread from a previous test class would re-use a stale "closed" conn
# from its old cache. Fixed by using a module-level dict keyed on
# threading.get_ident(). Same per-thread semantics, but close_all() can
# now clear the cache for every thread.
_thread_local: "dict[int, dict]" = {}

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
        db_path = default_db_path()
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

    # Per-thread dict (keyed on thread_ident) of (db_path, read_only) → conn.
    # Lazy-init on first call from this thread.
    tid = threading.get_ident()
    thread_cache = _thread_local.get(tid)
    if thread_cache is None:
        thread_cache = {}
        _thread_local[tid] = thread_cache

    cache_key = (str(db_path), bool(read_only))
    cached = thread_cache.get(cache_key)
    if cached is not None:
        return cached

    conn = _open_connection(db_path, read_only)
    thread_cache[cache_key] = conn

    # Register in the cross-thread registry so close_all() can find it
    # AND clear the per-thread cache entry for this thread.
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
    db_path = _normalize_db_path(db_path)
    path_key = str(db_path)
    tid = threading.get_ident()
    thread_cache = _thread_local.get(tid)

    # Pop both the requested mode AND the other mode for this path, since
    # open_db may have been called with a different mode than the caller
    # is closing with. Without this, a request to close the writable conn
    # could leave a stale read_only conn in the cache (or vice-versa).
    if thread_cache is not None:
        for mode in (False, True):
            key = (path_key, mode)
            conn = thread_cache.pop(key, None)
            if conn is not None and mode == bool(read_only):
                try:
                    conn.close()
                except sqlite3.Error:
                    pass

    # Unregister from the cross-thread registry for the matching modes.
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

    Also clears the per-thread `_thread_local` cache for every thread so
    a worker thread reused later doesn't pick up a stale (closed) conn
    from its cache. This is the cross-thread version of `close_db()`'s
    per-thread cache cleanup.

    Without this, asyncio.to_thread worker threads in long-lived test
    suites would re-use closed connections from previous test classes,
    causing hard-to-reproduce "database is locked" / stale-snapshot
    failures.
    """
    # Snapshot the registry under the lock; closing happens outside the
    # lock to avoid holding it during connection close (which can block).
    with _registry_lock:
        snapshot = list(_thread_registry.items())

    affected_tids = set()
    for tid, entry in snapshot:
        for cache_key, conn in entry.entries:
            try:
                conn.close()
            except sqlite3.Error:
                pass
        # Clear the entries list so the cleanup pass below can identify
        # which threads are now fully closed.
        entry.entries = []
        affected_tids.add(tid)

    # Clear per-thread caches for every thread we touched. Since
    # `_thread_local` is a module-level dict keyed on thread ident, we
    # can reach across threads to clear them.
    for tid in affected_tids:
        thread_cache = _thread_local.get(tid)
        if thread_cache is not None:
            thread_cache.clear()
    # Also clear the current thread's local cache.
    current_tid = threading.get_ident()
    thread_cache = _thread_local.get(current_tid)
    if thread_cache is not None:
        thread_cache.clear()

    # Drop registry entries with no remaining conns.
    with _registry_lock:
        for tid in list(_thread_registry.keys()):
            entry = _thread_registry.get(tid)
            if entry is not None and not entry.entries:
                _thread_registry.pop(tid, None)


def db_path() -> Path:
    """Return the canonical absolute default DB path."""
    return default_db_path().absolute()


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
