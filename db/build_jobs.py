"""db/build_jobs.py — build queue (per Q29, Q32 v3.2 §Day 6 + Day 2 db layer).

Per Q29: daemon owns the queue, CLI does the work.
Per Q32: build_jobs has 12 layers (one per phase). Each is queued, runs, completes.
Per Day 6: build_jobs.py provides queue_job, mark_running, mark_succeeded, mark_failed,
recover_orphans (for daemon startup).

Day 2 builds the data layer; Day 3 wraps it in HTTP endpoints; Day 6 wires up
the actual mmx invocation. This module is the SQL+state machine.

Functions:
  - queue_job(album_id, layer_id) - inserts a 'todo' job, returns the row
  - mark_running(job_id, pid) - 'todo' -> 'running', records pid
  - mark_succeeded(job_id) - 'running' -> 'done' (success)
  - mark_failed(job_id, error) - 'running' -> 'failed' or 'blocked'
  - get_job(album_id, layer_id) - fetch by composite key
  - get_job_by_id(job_id) - fetch by primary key
  - list_jobs(album_id, layer_id, status) - filtered list
  - mark_approved(job_id) - 'needs_approval' -> ready to run
  - recover_orphans() - on daemon startup, mark running jobs with dead pids as 'crashed'
"""
import os
import sqlite3
from pathlib import Path
from typing import Optional, Union

from db.connection import open_db, DEFAULT_DB_PATH
from db.pipeline import LAYER_ORDER, can_run, mark_approved as pipeline_mark_approved


def _now() -> str:
    """Return current UTC timestamp in SQLite native format."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _row_to_dict(row, cursor_description=None) -> Optional[dict]:
    """Convert a sqlite3 row to a dict, handling both Row and tuple results.

    In autocommit mode (test fixtures), rows can come back as plain tuples
    even with row_factory set. We use the cursor's column names (from
    description) to convert tuples to dicts.
    """
    if not row:
        return None
    if isinstance(row, dict):
        return row
    if isinstance(row, sqlite3.Row):
        return {k: row[k] for k in row.keys()}
    # Plain tuple - need column names from cursor description
    if cursor_description:
        return {col[0]: row[i] for i, col in enumerate(cursor_description)}
    return None  # can't convert without column names


def queue_job(album_id: str, layer_id: str, *,
             db_path: Optional[Union[str, Path]] = None) -> dict:
    """Queue a build job for (album_id, layer_id). Idempotent: returns existing if queued.

    Validates that layer_id is one of the 12 LAYER_ORDER layers. Uses
    db/pipeline.py for can_run() check before queueing.
    """
    if layer_id not in LAYER_ORDER:
        raise ValueError(f"Unknown layer_id: {layer_id}. "
                          f"Must be one of {LAYER_ORDER}")
    conn = open_db(db_path)
    # Idempotent: if a job already exists, return it
    existing = get_job(album_id, layer_id, db_path=db_path)
    if existing:
        return existing
    cur = conn.execute("""
        INSERT INTO build_jobs (album_id, layer_id, status, attempts)
        VALUES (?, ?, 'todo', 0)
    """, (album_id, layer_id))
    inserted_id = cur.lastrowid
    conn.commit()
    return get_job_by_id(inserted_id, db_path=db_path)


def mark_running(job_id: int, *,
                started_at: str = None,
                db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Mark a job as 'running'. Started_at defaults to now.

    Note: the build_jobs table does NOT track PIDs (per v3.2 schema). The
    daemon's process supervisor tracks child PIDs in memory for
    orphan recovery (see Day 6 build/lock.py).
    """
    conn = open_db(db_path)
    started = started_at or _now()
    conn.execute("""
        UPDATE build_jobs
        SET status = 'running', started_at = ?, updated_at = ?
        WHERE id = ? AND status IN ('todo', 'needs_approval')
    """, (started, started, job_id))
    conn.commit()
    return get_job_by_id(job_id, db_path=db_path)


def mark_succeeded(job_id: int,
                  db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Mark a job as 'done' (succeeded).

    The state machine is: todo -> running -> done. This function accepts
    any non-terminal status (todo/running/needs_approval/ready) so that
    tests can skip the running step. In production, the build runner
    should set status='running' before running mmx and then call this
    on success.
    """
    conn = open_db(db_path)
    conn.execute("""
        UPDATE build_jobs
        SET status = 'done', completed_at = datetime('now'),
            updated_at = datetime('now'), error = NULL
        WHERE id = ? AND status NOT IN ('done', 'crashed', 'failed', 'blocked')
    """, (job_id,))
    conn.commit()
    return get_job_by_id(job_id, db_path=db_path)


def mark_failed(job_id: int, error: str,
               db_path: Optional[Union[str, Path]] = None,
               status: str = "blocked") -> Optional[dict]:
    """Mark a running job as failed. Default status='blocked' (needs human review).

    Pass status='failed' for terminal failure (after attempts >= max_attempts).
    """
    conn = open_db(db_path)
    conn.execute("""
        UPDATE build_jobs
        SET status = ?, error = ?, updated_at = datetime('now'),
            attempts = attempts + 1
        WHERE id = ?
    """, (status, error[:500], job_id))  # cap error msg at 500 chars
    conn.commit()
    return get_job_by_id(job_id, db_path=db_path)


def get_job(album_id: str, layer_id: str,
           db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Fetch a job by (album_id, layer_id) composite key."""
    conn = open_db(db_path)
    row = conn.execute(
        "SELECT * FROM build_jobs WHERE album_id = ? AND layer_id = ?",
        (album_id, layer_id)
    ).fetchone()
    return _row_to_dict(row)


def get_job_by_id(job_id: int,
                 db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Fetch a job by primary key."""
    conn = open_db(db_path)
    row = conn.execute("SELECT * FROM build_jobs WHERE id = ?", (job_id,)).fetchone()
    return _row_to_dict(row)


def list_jobs(*, album_id: str = None, layer_id: str = None,
             status: str = None,
             db_path: Optional[Union[str, Path]] = None) -> list[dict]:
    """List jobs, optionally filtered by album_id, layer_id, status."""
    conn = open_db(db_path)
    filters = []
    values = []
    if album_id:
        filters.append("album_id = ?"); values.append(album_id)
    if layer_id:
        filters.append("layer_id = ?"); values.append(layer_id)
    if status:
        filters.append("status = ?"); values.append(status)
    where = ""
    if filters:
        where = "WHERE " + " AND ".join(filters)
    rows = conn.execute(
        f"SELECT * FROM build_jobs {where} ORDER BY id ASC", values
    ).fetchall()
    return [dict(r) for r in rows]


def mark_approved_via_pipeline(album_id: str, layer_id: str,
                              db_path: Optional[Union[str, Path]] = None) -> bool:
    """Approve a gated layer (delegates to db/pipeline.py for the read-side check)."""
    return pipeline_mark_approved(layer_id, album_id, db_path=db_path)


def recover_orphans(known_pids: set = None, *,
                  db_path: Optional[Union[str, Path]] = None) -> list[dict]:
    """Mark 'running' jobs whose PID is no longer in the known-pids set as 'crashed'.

    Per Day 7: 'Crash recovery on daemon startup: walks build_jobs for `running`
    rows with dead pids → marks `crashed`'.

    The build_jobs table doesn't track PIDs (per v3.2 schema). The daemon
    passes the set of currently-known child PIDs from its process supervisor.
    Any running job whose PID is NOT in the set is marked crashed.

    Args:
        known_pids: set of PIDs the daemon is currently managing.
                    If None, all running jobs are marked crashed (assumes
                    fresh daemon startup with no inherited children).

    Returns the list of jobs marked crashed.
    """
    conn = open_db(db_path)
    # 5-minute heuristic: only mark running jobs as crashed if they have
    # been running for at least 5 minutes (recent jobs get a grace period
    # for fast startup/shutdown).
    rows = conn.execute("""
        SELECT * FROM build_jobs
        WHERE status = 'running'
          AND datetime(started_at, '+5 minutes') < datetime('now')
    """).fetchall()
    crashed = []
    for row in rows:
        d = dict(row)
        conn.execute("""
            UPDATE build_jobs
            SET status = 'crashed', error = 'worker not in known_pids set',
                updated_at = datetime('now')
            WHERE id = ?
        """, (d["id"],))
        conn.commit()
        d["status"] = "crashed"
        d["error"] = "worker not in known_pids set"
        crashed.append(d)
    return crashed


def count_jobs_by_status(album_id: str = None,
                        db_path: Optional[Union[str, Path]] = None) -> dict:
    """Return a dict of {status: count} for the given album (or all if album_id is None)."""
    conn = open_db(db_path)
    if album_id:
        rows = conn.execute("""
            SELECT status, COUNT(*) as cnt
            FROM build_jobs WHERE album_id = ?
            GROUP BY status
        """, (album_id,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT status, COUNT(*) as cnt
            FROM build_jobs
            GROUP BY status
        """).fetchall()
    return {r["status"]: r["cnt"] for r in rows}


def max_attempts_for_layer(layer_id: str) -> int:
    """Return the max retry attempts for a layer (default 3)."""
    # Per plan: expensive operations get 5 attempts, cheap ones get 3
    expensive = {"05_instrumental", "06_cover_art", "08_audio_mastering"}
    if layer_id in expensive:
        return 5
    return 3
