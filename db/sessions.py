"""db/sessions.py — session state machine (per Q27, Q32 v3.2 §Day 2 + Day 4).

Per Q27: album_sessions is a first-class table. Sessions have a lifecycle:
  active → paused → done | active → blocked | active → done

Per Q32: max 3 active sessions enforced in CLI, NOT schema (Q32 says "CLI
guard, not schema CHECK"). The 12h idle auto-pause is a sweeper (Day 8).

Per Day 4: handlers/sessions.py wraps these functions with HTTP endpoints.
This module is the pure db layer.

Functions:
  - open_session(album_id) - creates a new session, checks max-3 guard
  - pause_session(uuid) - active → paused
  - resume_session(uuid) - paused → active, increments last_activity_at
  - complete_session(uuid) - active|paused → done
  - get_session(uuid) - returns session dict or None
  - list_sessions(album_id=None, status=None) - filters by album/status
  - count_active_sessions() - for the max-3 guard
  - touch_activity(uuid) - update last_activity_at to now (call on every event)

Return types: dict (sqlite3.Row) or list of dicts.
"""
import sqlite3
import uuid as uuid_lib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from db.connection import open_db, DEFAULT_DB_PATH

# Per Q32: max 3 active sessions
MAX_ACTIVE_SESSIONS = 3

# Per Q32: 12h idle auto-pause threshold
IDLE_THRESHOLD_HOURS = 12

# Valid status transitions
VALID_TRANSITIONS = {
    "active": {"paused", "done", "blocked"},
    "paused": {"active", "done"},
    "blocked": {"active", "paused", "done"},
    "done": set(),  # done is terminal
}


# ===== HELPERS =====

def _now_iso() -> str:
    """Return current UTC timestamp in SQLite DATETIME format.

    We use SQLite's native format ('YYYY-MM-DD HH:MM:SS') instead of
    ISO 8601 ('YYYY-MM-DDTHH:MM:SSZ') to ensure direct string comparison
    works in WHERE clauses. SQLite stores datetime as text, so the
    comparison is lexicographic; ISO 8601's 'T' separator > ' ' separator,
    which breaks < / > comparisons against CURRENT_TIMESTAMP.

    For external API responses (HTTP/JSON), convert to ISO 8601 at the
    boundary (e.g. in the daemon's response handler).
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _row_to_dict(row) -> Optional[dict]:
    """Convert sqlite3.Row to dict, or None if row is None."""
    return dict(row) if row else None


# ===== PUBLIC API =====

def open_session(album_id: str,
               *, db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Create a new session for the album.

    Returns the session dict, or None if the max-3 active guard fires
    (per Q32: cannot have more than 3 active sessions globally).

    The session starts with status='active' and last_activity_at=now.

    Race-safety: the count-then-insert sequence is wrapped in an IMMEDIATE
    transaction so concurrent open_session() calls serialize at the SQLite
    level. Without this, two threads both seeing active_count=2 would both
    insert and exceed the limit.
    """
    conn = open_db(db_path)

    # Max-3 active guard (per Q32) — wrapped in IMMEDIATE transaction so
    # concurrent open_session() calls cannot both observe count=2 and
    # both insert.
    conn.execute("BEGIN IMMEDIATE;")
    try:
        active_count = conn.execute(
            "SELECT COUNT(*) FROM album_sessions WHERE status = 'active'"
        ).fetchone()[0]
        if active_count >= MAX_ACTIVE_SESSIONS:
            conn.execute("ROLLBACK;")
            return None

        session_id = str(uuid_lib.uuid4())
        now = _now_iso()
        conn.execute("""
            INSERT INTO album_sessions (id, album_id, status, last_activity_at,
                                         created_at, closed_at)
            VALUES (?, ?, 'active', ?, ?, NULL)
        """, (session_id, album_id, now, now))
        conn.execute("COMMIT;")
    except Exception:
        try:
            conn.execute("ROLLBACK;")
        except sqlite3.Error:
            pass
        raise
    return get_session(session_id, db_path=db_path)


def pause_session(session_id: str,
                 *, db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Pause an active session. Returns the updated session.

    Per the state machine: active → paused. Blocked/paused cannot be paused.
    """
    conn = open_db(db_path)
    current = get_session(session_id, db_path=db_path)
    if not current:
        return None
    if "paused" not in VALID_TRANSITIONS.get(current["status"], set()):
        return None
    conn.execute("""
        UPDATE album_sessions SET status = 'paused', last_activity_at = ?
        WHERE id = ? AND status IN ('active', 'blocked')
    """, (_now_iso(), session_id))
    conn.commit()
    return get_session(session_id, db_path=db_path)


def resume_session(session_id: str,
                  *, db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Resume a paused/blocked session. Returns the updated session.

    Per the state machine: paused|blocked → active.
    Enforces max-3 active guard before resuming.
    """
    conn = open_db(db_path)
    current = get_session(session_id, db_path=db_path)
    if not current:
        return None
    if current["status"] not in ("paused", "blocked"):
        return None

    # Max-3 active guard
    active_count = conn.execute(
        "SELECT COUNT(*) FROM album_sessions WHERE status = 'active'"
    ).fetchone()[0]
    if active_count >= MAX_ACTIVE_SESSIONS:
        return None

    conn.execute("""
        UPDATE album_sessions SET status = 'active', last_activity_at = ?
        WHERE id = ? AND status IN ('paused', 'blocked')
    """, (_now_iso(), session_id))
    conn.commit()
    return get_session(session_id, db_path=db_path)


def complete_session(session_id: str,
                    *, db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Complete a session. Returns the updated session.

    Per the state machine: active|paused|blocked → done. done is terminal.
    """
    conn = open_db(db_path)
    current = get_session(session_id, db_path=db_path)
    if not current:
        return None
    if current["status"] == "done":
        return None  # already done

    conn.execute("""
        UPDATE album_sessions SET status = 'done', last_activity_at = ?, closed_at = ?
        WHERE id = ? AND status IN ('active', 'paused', 'blocked')
    """, (_now_iso(), _now_iso(), session_id))
    conn.commit()
    return get_session(session_id, db_path=db_path)


def get_session(session_id: str,
               *, db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Fetch a session by ID."""
    conn = open_db(db_path)
    row = conn.execute(
        "SELECT * FROM album_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    return _row_to_dict(row)


def list_sessions(*, album_id: str = None,
                 status: str = None,
                 db_path: Optional[Union[str, Path]] = None) -> list[dict]:
    """List sessions, optionally filtered by album_id and/or status.

    Per plan §7 Day 4 CLI: 'list sessions [--album=<slug>]' shows
    (uuid, status, idle_hours, created_at).
    """
    conn = open_db(db_path)
    filters = []
    values = []
    if album_id:
        filters.append("album_id = ?")
        values.append(album_id)
    if status:
        filters.append("status = ?")
        values.append(status)
    where = ""
    if filters:
        where = "WHERE " + " AND ".join(filters)
    rows = conn.execute(
        f"SELECT * FROM album_sessions {where} ORDER BY created_at DESC", values
    ).fetchall()
    return [dict(r) for r in rows]


def count_active_sessions(db_path: Optional[Union[str, Path]] = None) -> int:
    """Return the number of currently-active sessions. For the max-3 guard."""
    conn = open_db(db_path)
    return conn.execute(
        "SELECT COUNT(*) FROM album_sessions WHERE status = 'active'"
    ).fetchone()[0]


def touch_activity(session_id: str,
                  *, db_path: Optional[Union[str, Path]] = None) -> bool:
    """Update last_activity_at to now. Call on every chat event.

    Returns True if updated, False if session not found.
    """
    conn = open_db(db_path)
    cur = conn.execute("""
        UPDATE album_sessions SET last_activity_at = ?
        WHERE id = ? AND status = 'active'
    """, (_now_iso(), session_id))
    conn.commit()
    return cur.rowcount > 0


# ===== IDLE SWEEPER (manual trigger) =====

def pause_idle_sessions(album_id: str = None,
                       db_path: Optional[Union[str, Path]] = None) -> list[dict]:
    """Pause sessions that have been idle for >= IDLE_THRESHOLD_HOURS hours.

    Per Q32: 12h idle auto-pause. The Day 8 sweeper will call this. For
    now, exposes it as a function.

    Args:
        album_id: optional — if set, only pause sessions for this album.

    Returns:
        list of paused sessions.
    """
    conn = open_db(db_path)
    # SQL is built with ? parameters for both the cutoff interval (computed
    # in Python) and the optional album_id, so no f-string interpolation of
    # values into SQL text — safer than the previous f-string approach.
    if album_id:
        rows = conn.execute("""
            UPDATE album_sessions
            SET status = 'paused', last_activity_at = last_activity_at
            WHERE status = 'active'
              AND last_activity_at < datetime('now', ?)
              AND album_id = ?
            RETURNING *
        """, (f"-{IDLE_THRESHOLD_HOURS} hours", album_id)).fetchall()
    else:
        rows = conn.execute("""
            UPDATE album_sessions
            SET status = 'paused', last_activity_at = last_activity_at
            WHERE status = 'active'
              AND last_activity_at < datetime('now', ?)
            RETURNING *
        """, (f"-{IDLE_THRESHOLD_HOURS} hours",)).fetchall()
    conn.commit()
    return [dict(r) for r in rows]


def idle_hours(session_id: str,
              *, db_path: Optional[Union[str, Path]] = None) -> Optional[float]:
    """Return the hours since last_activity_at for a session.

    Returns None if session not found.
    """
    conn = open_db(db_path)
    row = conn.execute("""
        SELECT (julianday('now') - julianday(last_activity_at)) * 24.0 AS idle_hours
        FROM album_sessions WHERE id = ?
    """, (session_id,)).fetchone()
    return row["idle_hours"] if row else None
