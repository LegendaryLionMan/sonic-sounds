"""db/connection.py — SQLite connection + WAL + PRAGMAs (per Q24, Q26 v3.2 §Day 2).

The single entry point for opening a database connection. Implements:
- WAL mode + PRAGMAs on every connection open (per Q26)
- Idempotent open (the same path can be opened multiple times)
- Connection pool via SQLite's URI-based connection sharing

Per Q23: SQLite is the schema of record. Per Q26: WAL mode + PRAGMAs.
Per Q33, Q34: the studio reads via this module; events table is the source
of truth for chat history.

Design notes:
- We use sqlite3's connect() with check_same_thread=False so the same
  connection can be used across threads (the daemon runs sweepers and
  HTTP handlers in separate threads per Q26).
- row_factory is set to sqlite3.Row so callers can index by column name.
- foreign_keys is enforced (default disabled in SQLite).
- The .meta/ directory is created lazily if it doesn't exist.
- The connection wraps the .meta/album-studio.db path by default.
"""
import os
import sqlite3
from pathlib import Path
from typing import Optional, Union

# Default DB location (per Q25 + R10)
DEFAULT_DB_PATH = Path(".meta/album-studio.db")

# Pool of open connections keyed by db_path (per Q33, Q34)
# Within a single process, we share one connection per db_path.
_connections: dict[str, sqlite3.Connection] = {}


def open_db(db_path: Optional[Union[str, Path]] = None,
           *, read_only: bool = False) -> sqlite3.Connection:
    """Open (or reuse) a SQLite connection with WAL + PRAGMAs.

    Per Q26: every connection opens with:
      - PRAGMA journal_mode = WAL   (write-ahead log for concurrent reads)
      - PRAGMA foreign_keys = ON   (FK enforcement)
      - PRAGMA synchronous = NORMAL (WAL-safe; faster than FULL)
      - PRAGMA busy_timeout = 5s   (wait for a lock before failing)
      - PRAGMA cache_size = -8000  (8 MB cache)
      - PRAGMA temp_store = MEMORY (temp tables in memory)

    Args:
      db_path: absolute path to .db file. Defaults to .meta/album-studio.db.
      read_only: if True, opens with URI mode (uri=file:...?mode=ro).

    Returns:
      sqlite3.Connection with row_factory=sqlite3.Row.

    Note: most call sites should use open_db() without a path — the default
    .meta/album-studio.db is the canonical SQLite location per Q25.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    db_path = Path(db_path).absolute()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    cache_key = str(db_path)
    if cache_key in _connections:
        return _connections[cache_key]

    if read_only:
        # URI mode required for read-only
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    else:
        conn = sqlite3.connect(str(db_path), check_same_thread=False)

    # Apply PRAGMAs per Q26
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA cache_size = -8000;")
    conn.execute("PRAGMA temp_store = MEMORY;")

    # Project policy: row_factory allows column-name access
    conn.row_factory = sqlite3.Row

    # Cache the connection
    _connections[cache_key] = conn
    return conn


def close_db(db_path: Optional[Union[str, Path]] = None) -> None:
    """Close (and un-cache) the connection for the given db_path.

    Use this for shutdown; the connection pool is process-local.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    cache_key = str(Path(db_path).absolute())
    if cache_key in _connections:
        try:
            _connections[cache_key].close()
        except sqlite3.Error:
            pass
        del _connections[cache_key]


def close_all() -> None:
    """Close all cached connections. Use only at daemon shutdown."""
    for key in list(_connections.keys()):
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
    close_db()
