"""build/handlers_build.py - HTTP handlers for /api/build/* (Day 7).

Per plan section Day 7: "handlers/build.py: invoke endpoint (queues
job, returns job_id), status, cancel".

Public API:
  POST /api/build/invoke
    Body: {album_id, layer_id, prompt?, duration_sec?, lyrics?, size?, synchronous?}
      - synchronous=True (default): run the job inline, return when done.
      - synchronous=False: queue + return job_id immediately. Caller polls.
    Returns 201 with {job_id, status, output_path, ...}

  GET /api/build/jobs/<id>
    Returns the build_jobs row + computed status (terminal vs running).

  POST /api/build/jobs/<id>/cancel
    Marks a queued (todo) job as 'blocked'. Running jobs can't be
    cancelled mid-run (would require killing the subprocess — out of scope).

  GET /api/build/jobs?album_id=<id>&layer_id=<id>&status=<st>
    Lists build jobs matching the filters. Used by the studio's pipeline
    view to show "is this layer currently running?".

Layer resolution: pipeline-deps.json via db.pipeline.get_layer. The
handler rejects unknown layers with 400.
"""
from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Optional

from quart import Blueprint, request, jsonify

import db.build_jobs as db_build_jobs
from db.connection import open_db, close_db
from db.pipeline import get_layer

from build import invoke as build_invoke
from build.runner import run_job, JobOutcome

_log = logging.getLogger("sonic_studio.build.handlers")

# Per plan Q32 / build/serve.py: artifact root defaults to ./albums/.
DEFAULT_OUTPUT_BASE = Path(r".\albums")


build_bp = Blueprint("build", __name__)


async def _run(fn, *args, **kwargs):
    """Offload a sync db call to a thread, like handlers_sessions.py does."""
    def _wrapped():
        try:
            db_conn_close = close_db
            return fn(*args, **kwargs)
        finally:
            close_db()
    return await asyncio.to_thread(_wrapped)


@build_bp.route("/api/build/invoke", methods=["POST"])
async def invoke_endpoint():
    """Queue + (optionally) run a build job.

    Body: {album_id, layer_id, prompt?, duration_sec?, lyrics?, size?, synchronous?}

    If synchronous=True (default for studio's [invoke] button), the job
    runs to completion before the response is sent. Otherwise the job
    is queued (status='todo') and the caller polls /api/build/jobs/<id>.

    Returns 201 with {job_id, status, output_path, ...}
    """
    payload: Any = await request.get_json(silent=True) or {}

    album_id = payload.get("album_id")
    layer_id = payload.get("layer_id")
    synchronous = payload.get("synchronous", True)

    if not album_id or not layer_id:
        return jsonify({"error": "album_id and layer_id are required"}), 400

    # Validate the layer is known (raises KeyError if not)
    try:
        layer = get_layer(layer_id)
    except KeyError:
        return jsonify({"error": f"unknown layer_id: {layer_id!r}"}), 400

    # Validate the album exists — defensive even though FK should catch this
    from db.albums import get_album
    if get_album(album_id) is None:
        return jsonify({"error": f"unknown album_id: {album_id!r}"}), 400

    # Queue the job (idempotent — returns existing if already queued)
    job = await _run(db_build_jobs.queue_job, album_id, layer_id)

    if not synchronous:
        return jsonify({
            "job_id": job["id"],
            "status": job["status"],
            "queued": True,
        }), 202

    # Synchronous path: run inline, return the outcome.
    # We need a session_id for the events log; use <build> like the runner does.
    out_base_path = payload.get("output_base")
    output_base = Path(out_base_path) if out_base_path else DEFAULT_OUTPUT_BASE

    # Run on a thread (the runner itself is sync); the build runner
    # doesn't need an open DB conn passed in (it uses open_db()).
    def _do_run():
        # Use the global run_job but with our kwargs
        from build.runner import run_job as _run_job
        return _run_job(job["id"], output_base=output_base,
                        retry_on_transport_error=False)
    outcome: JobOutcome = await asyncio.to_thread(_do_run)

    # Refetch the row so we return DB-canonical status
    row = await _run(db_build_jobs.get_job_by_id, job["id"])
    return jsonify({
        "job_id": job["id"],
        "status": row["status"] if row else outcome.status,
        "output_path": outcome.output_path,
        "exit_code": outcome.exit_code,
        "elapsed_sec": outcome.elapsed_sec,
        "error": outcome.error,
    }), 200 if outcome.ok else 500


@build_bp.route("/api/build/jobs/<int:job_id>", methods=["GET"])
async def get_job_endpoint(job_id: int):
    """Return a single build_jobs row with current status."""
    row = await _run(db_build_jobs.get_job_by_id, job_id)
    if row is None:
        return jsonify({"error": f"job {job_id} not found"}), 404
    # Synthesize a more useful status: 'queued' for todo, 'in_progress'
    # for running, terminal states for done/failed/blocked/crashed.
    row["ui_status"] = _ui_status(row.get("status", "unknown"))
    return jsonify(row), 200


@build_bp.route("/api/build/jobs/<int:job_id>/cancel", methods=["POST"])
async def cancel_job_endpoint(job_id: int):
    """Cancel a queued (status='todo') job.

    Running jobs can't be cancelled — the daemon would need to kill the
    subprocess, which is out of scope for Day 7. Returns 409 if the job
    isn't in a cancellable state.
    """
    row = await _run(db_build_jobs.get_job_by_id, job_id)
    if row is None:
        return jsonify({"error": f"job {job_id} not found"}), 404
    if row["status"] != "todo":
        return jsonify({
            "error": f"cannot cancel job in status {row['status']!r}",
            "current_status": row["status"],
        }), 409
    # Use mark_failed with status='blocked' as our "cancelled" state.
    await _run(db_build_jobs.mark_failed, job_id,
                error="cancelled by user", status="blocked")
    return jsonify({"job_id": job_id, "status": "blocked"}), 200


@build_bp.route("/api/build/jobs", methods=["GET"])
async def list_jobs_endpoint():
    """List build jobs, optionally filtered by album_id/layer_id/status."""
    album_id = request.args.get("album_id")
    layer_id = request.args.get("layer_id")
    status = request.args.get("status")
    rows = await _run(
        db_build_jobs.list_jobs,
        album_id=album_id, layer_id=layer_id, status=status,
    )
    # Annotate each row with ui_status for the client
    for r in rows:
        r["ui_status"] = _ui_status(r.get("status", "unknown"))
    return jsonify(rows), 200


def _ui_status(db_status: str) -> str:
    """Translate db status to a UI-friendly name."""
    return {
        "todo": "queued",
        "needs_approval": "awaiting_approval",
        "ready": "ready",
        "running": "in_progress",
        "done": "succeeded",
        "blocked": "blocked",
        "failed": "failed",
        "crashed": "failed",  # aliased to failed for the UI
    }.get(db_status, db_status)
