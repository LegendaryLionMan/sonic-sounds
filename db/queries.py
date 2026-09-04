"""db/queries.py — common query helpers (per v3.2 §Day 2 + §7).

Per the plan: "db/queries.py" is a small layer of common query helpers
that the handlers (Day 4) and CLI (Day 2) call. This module is read-only —
writes go through albums/sessions/events/build_jobs.

Functions:
  - dashboard_summary(album_id) - returns the album + active sessions + recent events + build_jobs status
  - recent_albums_with_progress(limit) - top N albums with completion %
  - session_chat_history(session_id, limit) - last N events for the studio UI
  - build_jobs_for_album(album_id) - all jobs for an album, grouped by status
  - global_status() - 4-line summary for `python -m tools.sonic_sounds status`
"""
import sqlite3
from pathlib import Path
from typing import Optional, Union

from db.connection import open_db, DEFAULT_DB_PATH


def dashboard_summary(album_id: str,
                    db_path: Optional[Union[str, Path]] = None) -> dict:
    """Return the dashboard view for a single album: album + sessions + jobs summary."""
    conn = open_db(db_path)
    # Album
    album_row = conn.execute(
        "SELECT * FROM albums WHERE id = ?", (album_id,)
    ).fetchone()
    if not album_row:
        return {}
    album = dict(album_row)

    # Sessions
    sessions = [dict(r) for r in conn.execute(
        "SELECT * FROM album_sessions WHERE album_id = ? ORDER BY created_at DESC",
        (album_id,)
    ).fetchall()]

    # Build jobs
    jobs = [dict(r) for r in conn.execute(
        "SELECT * FROM build_jobs WHERE album_id = ? ORDER BY layer_id",
        (album_id,)
    ).fetchall()]

    # Tracks
    tracks = [dict(r) for r in conn.execute(
        "SELECT * FROM tracks WHERE album_id = ? ORDER BY track_num",
        (album_id,)
    ).fetchall()]

    return {
        "album": album,
        "sessions": sessions,
        "tracks": tracks,
        "jobs": jobs,
    }


def recent_albums_with_progress(limit: int = 10,
                              db_path: Optional[Union[str, Path]] = None) -> list[dict]:
    """List recent albums with build job progress.

    Returns: [{album: {...}, total_jobs: 12, done_jobs: 9, progress: 0.75}, ...]
    """
    conn = open_db(db_path)
    albums = [dict(r) for r in conn.execute("""
        SELECT a.*, COUNT(j.id) as total_jobs,
               SUM(CASE WHEN j.status = 'done' THEN 1 ELSE 0 END) as done_jobs
        FROM albums a
        LEFT JOIN build_jobs j ON j.album_id = a.id
        GROUP BY a.id
        ORDER BY a.created_at DESC
        LIMIT ?
    """, (limit,)).fetchall()]
    for a in albums:
        total = a.get("total_jobs", 0) or 0
        done = a.get("done_jobs", 0) or 0
        a["progress"] = done / total if total > 0 else 0.0
    return albums


def session_chat_history(session_id: str, limit: int = 100,
                       db_path: Optional[Union[str, Path]] = None) -> list[dict]:
    """Return the most recent events for a session (for the studio chat panel)."""
    conn = open_db(db_path)
    rows = conn.execute("""
        SELECT * FROM events
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (session_id, limit)).fetchall()
    return [dict(r) for r in rows]


def build_jobs_for_album(album_id: str,
                        db_path: Optional[Union[str, Path]] = None) -> dict:
    """Return build jobs for an album, grouped by status."""
    conn = open_db(db_path)
    jobs = [dict(r) for r in conn.execute(
        "SELECT * FROM build_jobs WHERE album_id = ? ORDER BY layer_id",
        (album_id,)
    ).fetchall()]

    by_status = {}
    for j in jobs:
        status = j.get("status", "unknown")
        by_status.setdefault(status, []).append(j)

    return by_status


def global_status(db_path: Optional[Union[str, Path]] = None) -> dict:
    """Return a 4-line summary for `python -m tools.sonic_sounds status`.

    Per plan §7 Day 2 verification: 'python -m tools.sonic_sounds status' shows
    (active sessions / paused / done albums / quota remaining).
    """
    conn = open_db(db_path)
    # Active sessions
    active = conn.execute(
        "SELECT COUNT(*) as cnt FROM album_sessions WHERE status = 'active'"
    ).fetchone()["cnt"]
    # Paused sessions
    paused = conn.execute(
        "SELECT COUNT(*) as cnt FROM album_sessions WHERE status = 'paused'"
    ).fetchone()["cnt"]
    # Done albums
    done_albums = conn.execute(
        "SELECT COUNT(*) as cnt FROM albums WHERE status = 'done'"
    ).fetchone()["cnt"]
    # Quota (last snapshot)
    quota_row = conn.execute("""
        SELECT model_kind, interval_pct FROM quota_snapshots
        ORDER BY captured_at DESC LIMIT 2
    """).fetchall()
    quota = {r["model_kind"]: r["interval_pct"] for r in quota_row}
    # Total albums
    total_albums = conn.execute(
        "SELECT COUNT(*) as cnt FROM albums"
    ).fetchone()["cnt"]
    # Total tracks
    total_tracks = conn.execute(
        "SELECT COUNT(*) as cnt FROM tracks"
    ).fetchone()["cnt"]

    return {
        "active_sessions": active,
        "paused_sessions": paused,
        "done_albums": done_albums,
        "total_albums": total_albums,
        "total_tracks": total_tracks,
        "quota_remaining": quota,
    }


def format_status_4line(status: dict) -> str:
    """Format the status dict as a 4-line CLI output per plan §7."""
    q = status.get("quota_remaining", {})
    general = f"{q.get('general', 'N/A')}%" if q.get("general") is not None else "N/A"
    video = f"{q.get('video', 'N/A')}%" if q.get("video") is not None else "N/A"
    lines = [
        f"active sessions: {status.get('active_sessions', 0)}/3",
        f"paused: {status.get('paused_sessions', 0)}",
        f"done albums: {status.get('done_albums', 0)}/{status.get('total_albums', 0)}",
        f"quota remaining: general {general}, video {video}",
    ]
    return "\n".join(lines)
