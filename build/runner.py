"""build/runner.py — Orchestrate a single build job end-to-end (Day 6).

Per plan section Day 6: "build/runner.py: subprocess management
(spawn CLI, watch exit, write events)". The runner:
  1. Acquires the build lock (build.lock.build_lock)
  2. Marks the build_job row as 'running' with started_at
  3. Dispatches via build.invoke.invoke()
  4. Writes events to the events log (build start, progress, result)
  5. Marks the job as 'succeeded' or 'failed'
  6. Releases the lock

Public API:
  run_job(job_id) -> JobOutcome  # synchronous, returns result

  run_due_jobs() -> int          # scan queue_job() for 'todo' jobs,
                                  # returns count of jobs started
                                  # (intended for the daemon's main
                                  # thread polling loop)

The runner does NOT spawn the CLI in a background thread — the daemon's
caller (HTTP handler or background sweep) is responsible for yielding.
This keeps the implementation testable without subprocess mocking.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import db.build_jobs as db_build_jobs
import db.events as db_events
from db.connection import open_db, close_db
from db.pipeline import get_layer

from build import invoke as build_invoke
from build.lock import build_lock

_log = logging.getLogger("sonic_studio.build.runner")

# Per Q32 / Day 8 plan: artifacts land in <output_base>/<album>/<layer>/
DEFAULT_OUTPUT_BASE = Path(r".\albums")


@dataclass
class JobOutcome:
    """Outcome of running a single build job."""
    job_id: int
    status: str         # 'succeeded' | 'failed' | 'crashed'
    exit_code: int
    output_path: Optional[str] = None
    error: Optional[str] = None
    elapsed_sec: float = 0.0

    @property
    def ok(self) -> bool:
        return self.status == "succeeded"


def run_job(job_id: int, *, output_base: Optional[Path] = None,
            retry_on_transport_error: bool = True) -> JobOutcome:
    """Run a single build_jobs row to completion. Synchronous.

    Caller is responsible for yielding control (asyncio.sleep or thread
    pool) if multiple jobs need to run in parallel. SQLite's
    busy_timeout=5000ms handles concurrent writers at the db level.

    Steps:
      1. Acquire the build lock (per-album serialization)
      2. Mark job as 'running' (started_at = now)
      3. Write a 'build_started' event
      4. Resolve the layer via db.pipeline.get_layer
      5. Dispatch via build.invoke.invoke()
      6. Mark job as 'succeeded' (with output_path) or 'failed' (with error)
      7. Write a 'build_finished' / 'build_failed' event
      8. Return JobOutcome

    On exception (not just mmx failure), the job is marked 'failed'
    with the exception text, AND the event log records 'build_crashed'.
    """
    start = time.monotonic()
    job = db_build_jobs.get_job_by_id(job_id)
    if job is None:
        return JobOutcome(job_id=job_id, status="failed",
                          exit_code=1, error=f"job {job_id} not found")

    album_id = job["album_id"]
    layer_id = job["layer_id"]

    # Resolve the layer (mmx_action, approval_required, etc.)
    try:
        layer = get_layer(layer_id)
    except KeyError:
        err = f"unknown layer_id: {layer_id!r}"
        _log.error(err)
        db_build_jobs.mark_failed(job_id, error=err, exit_code=1, status="failed")
        return JobOutcome(job_id=job_id, status="failed", exit_code=1, error=err)

    out_base = output_base or DEFAULT_OUTPUT_BASE
    action = layer.get("mmx_action")

    try:
        with build_lock(album_id):
            # Mark running
            db_build_jobs.mark_running(job_id)

            # Write build_started event
            db_events.create_event(
                session_id=None,  # build events are global; album_id below provides album context
                role="system", kind="log",
                content=f"build_started: layer={layer_id} action={action!r}",
                album_id=album_id,
                payload={"job_id": job_id, "layer_id": layer_id, "phase": "build_started"},
            )

            # Dispatch (or no-op for action=None)
            result = build_invoke.invoke(
                action=action,
                album_id=album_id,
                layer_id=layer_id,
                output_base=out_base,
                retry_on_transport_error=retry_on_transport_error,
            )

            elapsed = time.monotonic() - start

            if result.ok:
                db_build_jobs.mark_succeeded(
                    job_id, output_path=result.output_path,
                    elapsed_sec=elapsed, exit_code=0,
                )
                db_events.create_event(
                    session_id=None,  # build events are global; album_id below provides album context
                role="system", kind="log",
                    content=f"build_succeeded: {layer_id} in {elapsed:.1f}s",
                    album_id=album_id,
                    payload={"job_id": job_id, "layer_id": layer_id,
                              "phase": "build_succeeded",
                              "output_path": result.output_path,
                              "elapsed_sec": elapsed},
                )
                return JobOutcome(job_id=job_id, status="succeeded",
                                  exit_code=0, output_path=result.output_path,
                                  elapsed_sec=elapsed)
            else:
                err = f"mmx exited {result.exit_code}: {result.stderr[:200] if result.stderr else '(no stderr)'}"
                db_build_jobs.mark_failed(
                    job_id, error=err,
                    exit_code=result.exit_code,
                )
                db_events.create_event(
                    session_id=None,  # build events are global; album_id below provides album context
                role="system", kind="log",
                    content=f"build_failed: {layer_id} rc={result.exit_code}",
                    album_id=album_id,
                    payload={"job_id": job_id, "layer_id": layer_id,
                              "phase": "build_failed",
                              "exit_code": result.exit_code,
                              "stderr": result.stderr[:500] if result.stderr else None},
                )
                return JobOutcome(job_id=job_id, status="failed",
                                  exit_code=result.exit_code,
                                  error=err, elapsed_sec=elapsed)

    except Exception as e:
        elapsed = time.monotonic() - start
        err = f"{type(e).__name__}: {e}"
        _log.exception(f"build runner crashed for job {job_id}")
        try:
            db_build_jobs.mark_failed(job_id, error=err, exit_code=1)
            db_events.create_event(
                session_id=None,  # build events are global; album_id below provides album context
                role="system", kind="log",
                content=f"build_crashed: {layer_id} {err}",
                album_id=album_id,
                payload={"job_id": job_id, "layer_id": layer_id,
                          "phase": "build_crashed", "error": err},
            )
        except Exception:
            _log.exception("failed to record crash state")
        return JobOutcome(job_id=job_id, status="crashed",
                          exit_code=1, error=err, elapsed_sec=elapsed)


def run_due_jobs(*, output_base: Optional[Path] = None,
                 max_jobs: int = 10) -> int:
    """Scan for jobs with status='todo' and run them. Returns count started.

    Intended for the daemon's main thread to call periodically. Stops at
    max_jobs to avoid monopolizing the loop.
    """
    started = 0
    pending = db_build_jobs.list_jobs(status="todo", limit=max_jobs)
    for job in pending:
        run_job(job["id"], output_base=output_base)
        started += 1
        if started >= max_jobs:
            break
    return started
