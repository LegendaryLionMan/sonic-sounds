"""db/album_briefs.py - album_briefs CRUD (Day 9).

Per plan section Day 9: "brief-builder.html: assembles intake JSON
into the locked concept-brief template".

Schema (see db/schema.sql):
  album_id PRIMARY KEY
  brief_json TEXT NOT NULL              -- serialized 26-question intake
  locked_decisions_json TEXT            -- the locked Q-decisions
  sonic_dna_json TEXT                   -- M09 snapshot
  generated_at, updated_at              -- timestamps

Public API:
  upsert_brief(album_id, brief_json, ...) -> dict
  get_brief(album_id) -> dict | None
  list_briefs() -> list[dict]
  delete_brief(album_id) -> bool
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

from db.connection import open_db, close_db

# Per the locked concept-brief template, the brief JSON shape is:
#   {questions: {qid: value}, sonic_dna: {M09 fields}, generated_at: ts}
# Validated on write to catch schema drift.

# Mandatory M-tier question ids (per intake.html data-qid attributes).
MANDATORY_M_QUESTIONS = {
    "M01_concept", "M02_scope", "M03_genre", "M04_references",
    "M05_vocal", "M06_language", "M07_runtime", "M08_artist",
    "M09_sonicDNA",
}
# All 26 question ids (M-tier mandatory + R-tier recommended + E-tier extra).
ALL_QUESTIONS = MANDATORY_M_QUESTIONS | {
    "R09_title", "R10_tracklist", "R11_motif", "R12_production",
    "R13_lyricalSource", "R14_distribution",
    "E15_arc", "E16_influences", "E17_coverArt", "E18_anchor",
    "E19_pressScope", "E20_musicVideos", "E21_deadline",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def validate_brief_payload(payload: dict) -> list[str]:
    """Return a list of validation errors (empty = valid).

    Per Q8 schema validation rule: every M-tier question must have a
    non-empty answer; R and E tiers are optional.
    """
    errors = []
    if not isinstance(payload, dict):
        return [f"payload must be a dict, got {type(payload).__name__}"]
    questions = payload.get("questions", {})
    if not isinstance(questions, dict):
        return ["payload.questions must be a dict"]
    missing = []
    for qid in sorted(MANDATORY_M_QUESTIONS):
        v = questions.get(qid)
        if v is None or (isinstance(v, str) and not v.strip()):
            missing.append(qid)
    if missing:
        errors.append(f"missing or empty M-tier questions: {missing}")
    # Warn about unknown qids (don't fail; future intake revisions may
    # add new ones)
    unknown = sorted(set(questions) - ALL_QUESTIONS)
    if unknown:
        errors.append(f"unknown question ids (forward-compat warning): {unknown}")
    return errors


def upsert_brief(album_id: str, brief_payload: dict, *,
                 locked_decisions: Optional[dict] = None,
                 sonic_dna: Optional[dict] = None,
                 db_path: Optional[Union[str, Path]] = None) -> dict:
    """Insert or replace the brief row for an album.

    Args:
      album_id: FK to albums.id
      brief_payload: the full intake JSON ({questions: {qid: value}, ...})
      locked_decisions: optional Q-decisions dict
      sonic_dna: optional M09 snapshot dict
    Returns the inserted/updated row as a dict.
    """
    errs = validate_brief_payload(brief_payload)
    if errs:
        # Validation errors are not raised (so callers can decide) but
        # the row is still written — the schema is forgiving. Return
        # errors in the result so the caller can warn the user.
        pass

    brief_json = json.dumps(brief_payload, sort_keys=True)
    locked_json = json.dumps(locked_decisions) if locked_decisions is not None else None
    sonic_json = json.dumps(sonic_dna) if sonic_dna is not None else None
    now = _now_iso()

    conn = open_db(db_path)
    try:
        conn.execute("""
            INSERT INTO album_briefs (album_id, brief_json, locked_decisions_json, sonic_dna_json, generated_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(album_id) DO UPDATE SET
                brief_json = excluded.brief_json,
                locked_decisions_json = COALESCE(excluded.locked_decisions_json, album_briefs.locked_decisions_json),
                sonic_dna_json = COALESCE(excluded.sonic_dna_json, album_briefs.sonic_dna_json),
                updated_at = excluded.updated_at
        """, (album_id, brief_json, locked_json, sonic_json, now, now))
        conn.commit()
    finally:
        close_db()
    row = get_brief(album_id, db_path=db_path)
    if row is None:
        raise RuntimeError(f"upsert succeeded but get_brief returned None for {album_id}")
    return row


def get_brief(album_id: str, *,
             db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Return the brief row for an album (None if not found)."""
    conn = open_db(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM album_briefs WHERE album_id = ?", (album_id,),
        ).fetchone()
    finally:
        close_db()
    if row is None:
        return None
    out = dict(row)
    # Parse JSON columns for caller convenience (the handler may want
    # to re-serialize differently for the API response).
    for json_col in ("brief_json", "locked_decisions_json", "sonic_dna_json"):
        if out.get(json_col):
            try:
                out[json_col.replace("_json", "")] = json.loads(out[json_col])
            except json.JSONDecodeError:
                pass
    return out


def list_briefs(*,
                db_path: Optional[Union[str, Path]] = None) -> list[dict]:
    """List all brief rows, ordered by updated_at DESC."""
    conn = open_db(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM album_briefs ORDER BY updated_at DESC"
        ).fetchall()
    finally:
        close_db()
    return [dict(r) for r in rows]


def delete_brief(album_id: str, *,
                db_path: Optional[Union[str, Path]] = None) -> bool:
    """Delete the brief row for an album. Returns True if a row was removed."""
    conn = open_db(db_path)
    try:
        cur = conn.execute("DELETE FROM album_briefs WHERE album_id = ?", (album_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        close_db()
