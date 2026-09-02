"""build/handlers_sessions.py — HTTP handlers for /api/sessions/* (Day 4).

Per PLAN-2026-08-09-v3.4 §Day 4:
- Session lifecycle endpoints: open, pause, resume, complete, query
- All async, all DB calls via asyncio.to_thread
- Race-safe open_session (BEGIN IMMEDIATE, max-3 guard) is in db/sessions.py;
  this handler just exposes it via HTTP and maps errors to status codes

State machine (per db/sessions.py):
  active   → paused | done | blocked
  paused   → active | done
  blocked  → active | paused | done
  done     → (terminal)

Endpoints registered:
  GET    /api/sessions                       — list (optional ?album=, ?status=)
  POST   /api/sessions                       — open new session (201/409)
  GET    /api/sessions/<id>                  — get one (404)
  POST   /api/sessions/<id>/pause            — pause active (200/404/409)
  POST   /api/sessions/<id>/resume           — resume paused/blocked (200/404/409)
  POST   /api/sessions/<id>/complete         — complete (200/404/409)
  GET    /api/sessions/<id>/idle_hours       — read idle hours (200/404)
  POST   /api/sessions/<id>/touch            — bump activity (200/404)
"""
import asyncio
from typing import Any

from quart import Blueprint, request, jsonify

from db import sessions as db_sessions
from db import connection as db_conn


sessions_bp = Blueprint("sessions", __name__)


async def _run(fn, *args, **kwargs):
    """Offload a sync db call to a thread, with full open/close per call.

    Why not use the per-thread connection cache: in async tests under
    Quart, requests land on whichever worker thread the executor picks,
    and the per-thread cache means later requests on the same worker
    might inherit stale state from a request that hit an exception. The
    diagnostic case was: open_session fired max-3 guard on the first
    attempt of test_open_session_409_max_active because the cache held
    a snapshot from a previous test's `count_active_sessions` call.

    Opening a fresh connection per call costs ~1ms but eliminates the
    cross-test state leak.
    """
    def _wrapped():
        try:
            db_conn.close_db()  # Clear any cached conn from this thread
            return fn(*args, **kwargs)
        finally:
            db_conn.close_db()
    return await asyncio.to_thread(_wrapped)


# ============================================================
# List + create
# ============================================================

@sessions_bp.route("/api/sessions", methods=["GET"])
async def list_sessions():
    album_id = request.args.get("album")
    status = request.args.get("status")
    rows = await _run(db_sessions.list_sessions, album_id=album_id, status=status)
    return jsonify(rows)


@sessions_bp.route("/api/sessions", methods=["POST"])
async def open_session():
    """Open a new session for the given album.

    Returns 201 with the session dict on success.
    Returns 409 if max-3 active guard fires (per Q32).
    Returns 400 if album_id is missing or album doesn't exist.
    """
    payload: Any = await request.get_json(silent=True) or {}
    album_id = payload.get("album_id")
    if not album_id:
        return jsonify({"error": "missing required field: album_id"}), 400

    # Validate album exists before opening (saves a session row we'd
    # otherwise have to clean up).
    from db import albums as db_albums
    album = await _run(db_albums.get_album, album_id)
    if not album:
        return jsonify({"error": f"album not found: {album_id}"}), 400

    sess = await _run(db_sessions.open_session, album_id)
    if not sess:
        # Max-3 active guard fired (db layer returned None).
        return jsonify({
            "error": "max active sessions reached",
            "max": db_sessions.MAX_ACTIVE_SESSIONS,
        }), 409
    return jsonify(sess), 201


# ============================================================
# Single-session operations
# ============================================================

@sessions_bp.route("/api/sessions/<session_id>", methods=["GET"])
async def get_session(session_id: str):
    row = await _run(db_sessions.get_session, session_id)
    if not row:
        return jsonify({"error": "session not found"}), 404
    return jsonify(row)


def _state_error(action: str, current_status: str) -> tuple[bool, str]:
    """Validate a state transition. Returns (ok, message).

    Mirrors db/sessions.py VALID_TRANSITIONS so we can give a clean 409
    rather than letting the db layer silently return None.
    """
    transitions = {
        "pause":    {"active"},
        "resume":   {"paused", "blocked"},
        "complete": {"active", "paused", "blocked"},
    }
    allowed = transitions.get(action, set())
    if current_status in allowed:
        return True, ""
    return False, f"cannot {action} session in status '{current_status}'"


async def _transition(session_id: str, action: str, db_fn):
    """Common helper for pause/resume/complete.

    Returns (status_code, body_dict) so the route can jsonify directly.
    """
    current = await _run(db_sessions.get_session, session_id)
    if not current:
        return 404, {"error": "session not found"}

    ok, msg = _state_error(action, current["status"])
    if not ok:
        return 409, {"error": msg}

    result = await _run(db_fn, session_id)
    if not result:
        # db layer returned None — race condition (e.g., another request
        # completed the session between our check and our update).
        return 409, {"error": f"session no longer in valid state for {action}"}
    return 200, result


@sessions_bp.route("/api/sessions/<session_id>/pause", methods=["POST"])
async def pause_session(session_id: str):
    code, body = await _transition(session_id, "pause", db_sessions.pause_session)
    return jsonify(body), code


@sessions_bp.route("/api/sessions/<session_id>/resume", methods=["POST"])
async def resume_session(session_id: str):
    code, body = await _transition(session_id, "resume", db_sessions.resume_session)
    return jsonify(body), code


@sessions_bp.route("/api/sessions/<session_id>/complete", methods=["POST"])
async def complete_session(session_id: str):
    code, body = await _transition(session_id, "complete", db_sessions.complete_session)
    return jsonify(body), code


# ============================================================
# Read-only helpers
# ============================================================

@sessions_bp.route("/api/sessions/<session_id>/idle_hours", methods=["GET"])
async def get_idle_hours(session_id: str):
    hours = await _run(db_sessions.idle_hours, session_id)
    if hours is None:
        return jsonify({"error": "session not found"}), 404
    return jsonify({"session_id": session_id, "idle_hours": hours})


@sessions_bp.route("/api/sessions/<session_id>/touch", methods=["POST"])
async def touch_session(session_id: str):
    """Bump last_activity_at to now (called on every chat event)."""
    ok = await _run(db_sessions.touch_activity, session_id)
    if not ok:
        return jsonify({"error": "session not found or not active"}), 404
    return jsonify({"session_id": session_id, "touched": True})
