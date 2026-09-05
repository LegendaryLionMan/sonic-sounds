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
             db_path: Optional[Union[str, Path]] = None,
             retry: bool = False) -> dict:
    """Queue a build job for (album_id, layer_id). Idempotent by default.

    Validates that layer_id is one of the 12 LAYER_ORDER layers. Uses
    db/pipeline.py for can_run() check before queueing.

    Default behavior is idempotent: if a job already exists, return it
    (no-op). Pass `retry=True` to explicitly re-queue an already-done
    or failed job — this resets its status to 'todo' and increments
    attempts. The error / output_path columns are cleared so the
    runner sees a fresh job.
    """
    if layer_id not in LAYER_ORDER:
        raise ValueError(f"Unknown layer_id: {layer_id}. "
                          f"Must be one of {LAYER_ORDER}")
    conn = open_db(db_path)
    existing = get_job(album_id, layer_id, db_path=db_path)
    if existing:
        if not retry:
            return existing
        # Explicit retry: reset the row so the runner sees a clean job.
        conn.execute("""
            UPDATE build_jobs
            SET status = 'todo',
                started_at = NULL,
                completed_at = NULL,
                error = NULL,
                output_path = NULL,
                elapsed_sec = NULL,
                exit_code = NULL,
                updated_at = datetime('now')
            WHERE id = ?
        """, (existing["id"],))
        conn.commit()
        return get_job_by_id(existing["id"], db_path=db_path)
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

    Accepts the post-approval `ready` state in addition to `todo` and
    `needs_approval`. Approval-required layers transition to `ready`
    via mark_approved() (db/pipeline.py) before becoming runnable.
    """
    conn = open_db(db_path)
    started = started_at or _now()
    conn.execute("""
        UPDATE build_jobs
        SET status = 'running', started_at = ?, updated_at = ?
        WHERE id = ? AND status IN ('todo', 'needs_approval', 'ready')
    """, (started, started, job_id))
    conn.commit()
    return get_job_by_id(job_id, db_path=db_path)


def mark_succeeded(job_id: int,
                  *,
                  output_path = None,
                  elapsed_sec = None,
                  exit_code: int = 0,
                  db_path = None) -> Optional[dict]:
    """Mark a job as 'done' (succeeded) with optional runner metadata.

    The state machine is: todo -> running -> done. This function accepts
    any non-terminal status so that tests can skip the running step.
    In production, the build runner should set status='running'
    before running mmx and then call this on success.

    Args:
      job_id: build_jobs.id
      output_path: optional path to generated artifact (Day 6 build runner)
      elapsed_sec: optional run duration in seconds
      exit_code: subprocess exit code (default 0 = success)
    """
    conn = open_db(db_path)
    conn.execute("""
        UPDATE build_jobs
        SET status = 'done',
            completed_at = datetime('now'),
            updated_at = datetime('now'),
            error = NULL,
            output_path = COALESCE(?, output_path),
            elapsed_sec = COALESCE(?, elapsed_sec),
            exit_code = ?
        WHERE id = ? AND status NOT IN ('done', 'crashed', 'failed', 'blocked')
    """, (output_path, elapsed_sec, exit_code, job_id))
    conn.commit()
    return get_job_by_id(job_id, db_path=db_path)


def mark_failed(job_id: int, error: str, *,
               exit_code: int = 1,
               status: str = "blocked",
               db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Mark a running job as failed. Default status='blocked' (needs human review).

    Pass status='failed' for terminal failure (after attempts >= max_attempts).
    exit_code records the subprocess rc that caused the failure.
    """
    conn = open_db(db_path)
    conn.execute("""
        UPDATE build_jobs
        SET status = ?, error = ?, updated_at = datetime('now'),
            attempts = attempts + 1,
            exit_code = ?
        WHERE id = ?
    """, (status, error[:500], exit_code, job_id))
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
             status: str = None, limit: int = None,
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
    sql = f"SELECT * FROM build_jobs {where} ORDER BY id ASC"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    rows = conn.execute(sql, values).fetchall()
    return [dict(r) for r in rows]


def mark_approved_via_pipeline(album_id: str, layer_id: str,
                              db_path: Optional[Union[str, Path]] = None) -> bool:
    """Approve a gated layer (delegates to db/pipeline.py for the read-side check)."""
    return pipeline_mark_approved(layer_id, album_id, db_path=db_path)


def recover_orphans(known_job_ids: set = None, *,
                  known_pids: set = None,
                  db_path: Optional[Union[str, Path]] = None) -> list[dict]:
    """Mark 'running' jobs whose worker is no longer alive as 'crashed'.

    Per Day 7: 'Crash recovery on daemon startup: walks build_jobs for `running`
    rows with dead pids → marks `crashed`'.

    IMPORTANT (2026-09-05 audit): The build_jobs table does NOT track PIDs
    (per v3.2 schema). The parameter is named `known_job_ids` to reflect
    that it accepts a set of build_jobs.id integers, not OS PIDs. Earlier
    versions of this function were named `known_pids` which was a
    documented footgun: callers that passed actual OS PIDs would see
    every running job marked crashed (because build_jobs.id is in a
    different namespace from PIDs). `known_pids` is still accepted as
    a deprecated alias for backward compat with existing test fixtures.

    Semantics:
      - known_job_ids=None (default) → marks ALL old running jobs as
        crashed (assumes fresh daemon startup with no inherited children).
      - known_job_ids=set() → marks ALL old running jobs as crashed.
      - known_job_ids={1, 2, 3} → marks running jobs crashed only if
        their row id is NOT in the set.

    A 5-minute grace period protects recently-started jobs from being
    marked crashed by a fast restart loop.
    """
    # Backwards-compat: `known_pids` is the old (misnamed) keyword. If
    # a caller passes it, use that value and warn. New code should pass
    # `known_job_ids`.
    if known_pids is not None and known_job_ids is None:
        import warnings
        warnings.warn(
            "recover_orphans(known_pids=...) is deprecated, use "
            "recover_orphans(known_job_ids=...) instead. The parameter "
            "accepts build_jobs.id integers, not OS PIDs.",
            DeprecationWarning,
            stacklevel=2,
        )
        known_job_ids = known_pids
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
        # known_job_ids is a set of build_jobs.id integers the daemon is
        # currently running in its in-memory worker table. Skip those.
        if known_job_ids is not None and d["id"] in known_job_ids:
            continue
        conn.execute("""
            UPDATE build_jobs
            SET status = 'crashed', error = 'worker not in known_job_ids set',
                updated_at = datetime('now')
            WHERE id = ?
        """, (d["id"],))
        conn.commit()
        d["status"] = "crashed"
        d["error"] = "worker not in known_job_ids set"
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
