"""db/events.py — paginated event log (per Q34 v3.2 §Day 2).

Per Q34: events table is the source of truth for chat history. Polling
2s for chat = pagination via `?since=<ts>`.

Per Day 5: studio.js polls events every 2s while session open, 30s idle.
The events endpoint returns events newer than the last seen timestamp.

Functions:
  - create_event(session_id, role, kind, content, payload) — append a row
  - list_events(session_id, since_ts, limit) — paginated read
  - get_event(event_id) — fetch a single event
  - events_after(session_id, since_ts) — convenience for polling

Roles: 'user' | 'assistant' | 'system' | 'tool'
Kinds: 'chat' | 'build' | 'quota' | 'system' | 'log'
"""
import json
import sqlite3
import uuid as uuid_lib
from pathlib import Path
from typing import Optional, Union

from db.connection import open_db, DEFAULT_DB_PATH


def _row_to_dict(row) -> Optional[dict]:
    return dict(row) if row else None


def create_event(session_id: str, role: str, kind: str, content: str = None,
               *, payload: dict = None,
               album_id: str = None,
               event_id: int = None,
               db_path: Optional[Union[str, Path]] = None) -> dict:
    """Append an event to the log.

    Args:
      session_id: required
      role: 'user' | 'assistant' | 'system' | 'tool'
      kind: 'chat' | 'build' | 'quota' | 'system' | 'log'
      content: main text (optional for system events)
      payload: structured data dict (JSON-serialized)
      album_id: optional album reference (for global events)
      event_id: explicit ID (defaults to auto-increment)

    Returns the inserted event dict.

    Side effect: if this is a chat event (user or assistant role) with
    a session_id, the session's last_activity_at is updated so the
    12h idle auto-pause sweeper doesn't prematurely pause an actively
    chatting session. Per CATCH-UP 2026-09-05 audit #15: previously the
    studio never called touch_activity on chat, so a busy chat session
    could be paused after 12h of inactivity even though the user was
    actively typing. Auto-touching here keeps the timestamp fresh
    without requiring every caller to remember.
    """
    conn = open_db(db_path)
    # `payload is not None` (not `if payload`) — empty dict {} is a
    # valid payload and must round-trip as {} not None.
    payload_json = json.dumps(payload) if payload is not None else None
    cur = conn.execute("""
        INSERT INTO events (id, session_id, album_id, role, kind, content, payload_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (event_id, session_id, album_id, role, kind, content, payload_json))
    inserted_id = cur.lastrowid
    conn.commit()
    # Auto-touch the session for chat events. Local import avoids the
    # events<->sessions circular import at module load.
    if session_id and role in ("user", "assistant") and kind == "chat":
        try:
            from db.sessions import touch_activity as _touch
            _touch(session_id, db_path=db_path)
        except Exception:
            # Best-effort: if the session row is missing or the db is
            # busy, don't fail the event write. The next event will
            # retry the touch.
            pass
    return get_event(inserted_id, db_path=db_path)


def list_events(session_id: str, *, since_ts: str = None,
               limit: int = 100, before_id: int = None,
               kind: str = None,
               db_path: Optional[Union[str, Path]] = None) -> list[dict]:
    """List events for a session, paginated.

    Per Q34: pagination via `?since=<ts>` (the polling pattern).
    The studio polls every 2s with since_ts = last_event_created_at + 1ms.

    Args:
      session_id: required
      since_ts: optional ISO timestamp string (return events NEWER than this)
      limit: max events to return (default 100)
      before_id: optional, for backward pagination
      kind: optional filter by event kind

    Returns list of events in ascending order (oldest first, then newer).
    """
    conn = open_db(db_path)
    filters = ["session_id = ?"]
    values = [session_id]
    if since_ts:
        filters.append("created_at > ?")
        values.append(since_ts)
    if before_id is not None:
        filters.append("id < ?")
        values.append(before_id)
    if kind:
        filters.append("kind = ?")
        values.append(kind)
    where = " AND ".join(filters)
    rows = conn.execute(
        f"SELECT * FROM events WHERE {where} ORDER BY id ASC LIMIT ?", (*values, limit)
    ).fetchall()
    return [dict(r) for r in rows]


def events_after(session_id: str, since_ts: str = "",
                *, limit: int = 100,
                db_path: Optional[Union[str, Path]] = None) -> list[dict]:
    """Convenience: events newer than since_ts (empty string = all)."""
    return list_events(session_id, since_ts=since_ts or None,
                       limit=limit, db_path=db_path)


def get_event(event_id: int,
             db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Fetch a single event by ID."""
    conn = open_db(db_path)
    row = conn.execute(
        "SELECT * FROM events WHERE id = ?", (event_id,)
    ).fetchone()
    return _row_to_dict(row)


def latest_event_id(session_id: str,
                   db_path: Optional[Union[str, Path]] = None) -> Optional[int]:
    """Return the most recent event ID for a session, or None."""
    conn = open_db(db_path)
    row = conn.execute(
        "SELECT MAX(id) as max_id FROM events WHERE session_id = ?",
        (session_id,)
    ).fetchone()
    return row["max_id"] if row and row["max_id"] is not None else None


def list_events_by_album(album_id: str, *, since_ts: str = None,
                         kind: str = None, limit: int = 100,
                         db_path: Optional[Union[str, Path]] = None) -> list[dict]:
    """List events for an album (any session or global).

    Returns rows where events.album_id = album_id, regardless of
    session_id. This includes "global" events (session_id IS NULL)
    written by the build runner (Day 6 / Day 7) — these never belong
    to a particular session but DO carry the album_id for context.

    Filters: since_ts (string compare against created_at), kind, limit.
    Sort: id ASC for stable polling.
    """
    conn = open_db(db_path)
    filters = ["album_id = ?"]
    values: list = [album_id]
    if since_ts:
        filters.append("created_at > ?"); values.append(since_ts)
    if kind:
        filters.append("kind = ?"); values.append(kind)
    sql = f"SELECT * FROM events WHERE {' AND '.join(filters)} ORDER BY id ASC"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    rows = conn.execute(sql, values).fetchall()
    return [dict(r) for r in rows]


def count_events(session_id: str,
                *, since_ts: str = None,
                kind: str = None,
                db_path: Optional[Union[str, Path]] = None) -> int:
    """Count events for a session, optionally filtered."""
    conn = open_db(db_path)
    filters = ["session_id = ?"]
    values = [session_id]
    if since_ts:
        filters.append("created_at > ?")
        values.append(since_ts)
    if kind:
        filters.append("kind = ?")
        values.append(kind)
    where = " AND ".join(filters)
    row = conn.execute(
        f"SELECT COUNT(*) as cnt FROM events WHERE {where}", values
    ).fetchone()
    return row["cnt"]


