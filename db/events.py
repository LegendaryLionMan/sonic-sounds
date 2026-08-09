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
    """
    import json
    conn = open_db(db_path)
    payload_json = json.dumps(payload) if payload else None
    cur = conn.execute("""
        INSERT INTO events (id, session_id, album_id, role, kind, content, payload_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (event_id, session_id, album_id, role, kind, content, payload_json))
    inserted_id = cur.lastrowid
    conn.commit()
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


