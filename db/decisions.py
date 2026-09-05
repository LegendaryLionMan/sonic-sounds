"""db/decisions.py — Aldecision Verdicts (per Q30 + v3.2 §5 META-DECISIONS).

The decisions table is the source of truth for "what did the user lock,
why, when, in which doc". It's how the walkthrough is persisted beyond
any one chat session.

Per the schema, every decision has:
  - code (e.g. "M01", "R12", "Q45")
  - tier ("mandatory" | "recommended" | "extra")
  - question (the verbatim question)
  - answer (the verbatim answer)
  - rationale (one paragraph)
  - locked_at (ISO timestamp)
  - source_doc (which META-DECISIONS file)

Functions:
  - create_decision(code, tier, question, answer, ...) — append
  - get_decision(code) — fetch by code (one decision per code typically)
  - list_decisions(album_id, tier) — filters
  - update_decision(code, ...) — modify answer/rationale
  - delete_decision(code) — soft or hard delete
"""
import sqlite3
from pathlib import Path
from typing import Optional, Union

from db.connection import open_db, DEFAULT_DB_PATH


def _row_to_dict(row) -> Optional[dict]:
    return dict(row) if row else None


# Module-level sentinel for update_decision() — distinguishes "key
# absent from kwargs" from "key present with None". Lives at module
# scope so the default is a stable identity (not re-created per call).
_SENTINEL = object()


def create_decision(code: str, tier: str, question: str = None,
                   answer: str = None, *,
                   rationale: str = None,
                   source_doc: str = None,
                   session_id: str = None,
                   album_id: str = None,
                   db_path: Optional[Union[str, Path]] = None) -> dict:
    """Append a decision. Returns the inserted row (or first row if composite key).

    The (album_id, code) pair is intended to be unique per album. We append
    rather than upsert — multiple walks may produce multiple rows for the
    same code (each walk is its own history).

    `locked_at` is set to the current UTC time on create (with
    subsecond precision so consecutive creates + patches stay strictly
    ordered) — a fresh decision IS the lock event (otherwise the
    timestamp would be unknown until the user PATCHes, which they may
    never do).

    Per CATCH-UP 2026-09-05 audit: was previously local-time via
    `_time.localtime()` even though the docstring says ISO 8601 UTC.
    Now uses `datetime.now(timezone.utc)` to match the docstring.
    """
    from datetime import datetime, timezone
    locked_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") + f".{int(datetime.now(timezone.utc).timestamp()*1000)%1000:03d}"
    conn = open_db(db_path)
    cur = conn.execute("""
        INSERT INTO decisions (session_id, album_id, code, tier, question,
                                answer, rationale, source_doc, locked_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (session_id, album_id, code, tier, question, answer, rationale,
          source_doc, locked_at))
    inserted_id = cur.lastrowid
    conn.commit()
    return get_decision_by_id(inserted_id, db_path=db_path)


def get_decision_by_id(decision_id: int,
                       db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Fetch a decision by primary key."""
    conn = open_db(db_path)
    row = conn.execute(
        "SELECT * FROM decisions WHERE id = ?", (decision_id,)
    ).fetchone()
    return _row_to_dict(row)


def get_decision(code: str, *, album_id: str = None,
                db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Fetch a decision by code (and optionally album_id). Returns the most recent."""
    conn = open_db(db_path)
    if album_id:
        row = conn.execute("""
            SELECT * FROM decisions WHERE code = ? AND album_id = ?
            ORDER BY id DESC LIMIT 1
        """, (code, album_id)).fetchone()
    else:
        row = conn.execute("""
            SELECT * FROM decisions WHERE code = ?
            ORDER BY id DESC LIMIT 1
        """, (code,)).fetchone()
    return _row_to_dict(row)


def list_decisions(*, album_id: str = None,
                  tier: str = None, code: str = None,
                  session_id: str = None,
                  db_path: Optional[Union[str, Path]] = None) -> list[dict]:
    """List decisions, optionally filtered by album_id, tier, code, session_id."""
    conn = open_db(db_path)
    filters = []
    values = []
    if album_id:
        filters.append("album_id = ?"); values.append(album_id)
    if tier:
        filters.append("tier = ?"); values.append(tier)
    if code:
        filters.append("code = ?"); values.append(code)
    if session_id:
        filters.append("session_id = ?"); values.append(session_id)
    where = ""
    if filters:
        where = "WHERE " + " AND ".join(filters)
    rows = conn.execute(
        f"SELECT * FROM decisions {where} ORDER BY id ASC", values
    ).fetchall()
    return [dict(r) for r in rows]


def update_decision(decision_id: int, *,
                  answer=_SENTINEL,
                  rationale=_SENTINEL,
                  source_doc=_SENTINEL,
                  db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Update a decision's answer/rationale/source_doc.

    Sentinel-based API distinguishes three cases:
    - Key absent from kwargs → don't touch the field
    - Key present with non-None value → update to that value
    - Key present with None → set the field to NULL (explicit clear)

    This matches the handler's three-way semantics (omit = no-op,
    null = clear, value = update). The default sentinel is module-level
    so callers can use the function without specifying all three args.

    `locked_at` includes subsecond precision (Python-side) so two
    consecutive patches in the same wall-clock second produce
    monotonically-increasing timestamps. Without this, locked_at
    collisions would silently break audit-trail ordering.

    Timestamps are UTC (per CATCH-UP 2026-09-05 audit). Earlier versions
    used `_time.localtime()` which is host-local; the schema column is
    type-agnostic so this is a cosmetic-but-meaningful fix for clients
    that compare decisions across timezones.
    """
    from datetime import datetime, timezone
    def _utc_now_with_ms():
        now = datetime.now(timezone.utc)
        return now.strftime("%Y-%m-%d %H:%M:%S") + f".{int(now.timestamp()*1000)%1000:03d}"
    conn = open_db(db_path)
    fields = []
    values = []
    if answer is not _SENTINEL:
        if answer is None:
            fields.append("answer = NULL")
        else:
            fields.append("answer = ?"); values.append(answer)
    if rationale is not _SENTINEL:
        if rationale is None:
            fields.append("rationale = NULL")
        else:
            fields.append("rationale = ?"); values.append(rationale)
    if source_doc is not _SENTINEL:
        if source_doc is None:
            fields.append("source_doc = NULL")
        else:
            fields.append("source_doc = ?"); values.append(source_doc)
    if not fields:
        return get_decision_by_id(decision_id, db_path=db_path)
    # Subsecond precision: %Y-%m-%d %H:%M:%S.fff (SQLite accepts this). UTC.
    fields.append("locked_at = ?"); values.append(_utc_now_with_ms())
    values.append(decision_id)
    conn.execute(f"UPDATE decisions SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    return get_decision_by_id(decision_id, db_path=db_path)


def delete_decision(decision_id: int,
                   db_path: Optional[Union[str, Path]] = None) -> bool:
    """Hard-delete a decision. Returns True if deleted."""
    conn = open_db(db_path)
    cur = conn.execute("DELETE FROM decisions WHERE id = ?", (decision_id,))
    conn.commit()
    return cur.rowcount > 0


def count_decisions(*, album_id: str = None,
                   tier: str = None,
                   db_path: Optional[Union[str, Path]] = None) -> int:
    """Count decisions matching filters."""
    conn = open_db(db_path)
    filters = []
    values = []
    if album_id:
        filters.append("album_id = ?"); values.append(album_id)
    if tier:
        filters.append("tier = ?"); values.append(tier)
    where = ""
    if filters:
        where = "WHERE " + " AND ".join(filters)
    row = conn.execute(
        f"SELECT COUNT(*) as cnt FROM decisions {where}", values
    ).fetchone()
    return row["cnt"]
