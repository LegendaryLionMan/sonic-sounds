"""build/handlers_decisions.py — HTTP handlers for /api/decisions/*.

Day 5. Decisions are the album-studio's persistent "what did the user
lock, why, when, in which doc" log. Schema:
  code (e.g. "M01") + tier ("mandatory" | "recommended" | "extra")
  + question, answer, rationale, source_doc, session_id, album_id

There's no state machine on decisions (one row per lock; subsequent
walks append rather than upsert — per db/decisions.py). CRUD endpoints
mirror what `db/decisions.py` exposes:

  GET    /api/decisions                       — list (filters: ?album=, ?tier=, ?code=)
  POST   /api/decisions                       — append (201/400)
  GET    /api/decisions/<id>                  — get one (404)
  PATCH  /api/decisions/<id>                  — update answer/rationale/source_doc (200/404)
  DELETE /api/decisions/<id>                  — hard delete (204/404)

Plus session-scoped convenience routes for the studio page:
  GET    /api/sessions/<id>/decisions         — list for a session
  GET    /api/albums/<id>/decisions           — list for an album
"""
import asyncio
from typing import Any

from quart import Blueprint, request, jsonify

from db import decisions as db_decisions
from db import connection as db_conn


decisions_bp = Blueprint("decisions", __name__)


async def _run(fn, *args, **kwargs):
    """Offload a sync db call to a thread, with full open/close per call.

    Same rationale as handlers_sessions.py / handlers_events.py —
    fresh connection per request avoids stale-thread state.
    """
    def _wrapped():
        try:
            db_conn.close_db()
            return fn(*args, **kwargs)
        finally:
            db_conn.close_db()
    return await asyncio.to_thread(_wrapped)


# ============================================================
# List + create
# ============================================================

@decisions_bp.route("/api/decisions", methods=["GET"])
async def list_decisions():
    """List decisions with optional filters.

    Query params (all optional):
      album: filter by album_id
      tier: filter by tier ('mandatory' | 'recommended' | 'extra')
      code: filter by code (e.g. 'M01')
      session: filter by session_id
    """
    rows = await _run(
        db_decisions.list_decisions,
        album_id=request.args.get("album"),
        tier=request.args.get("tier"),
        code=request.args.get("code"),
        session_id=request.args.get("session"),
    )
    return jsonify(rows)


@decisions_bp.route("/api/decisions", methods=["POST"])
async def create_decision():
    """Append a new decision to the log.

    Required fields: code, tier
    Optional: question, answer, rationale, source_doc, session_id, album_id

    Returns 201 with the inserted decision dict on success.
    Returns 400 if required fields are missing or tier is invalid.
    """
    payload: Any = await request.get_json(silent=True) or {}

    code = payload.get("code")
    tier = payload.get("tier")
    question = payload.get("question")
    answer = payload.get("answer")
    rationale = payload.get("rationale")
    source_doc = payload.get("source_doc")
    session_id = payload.get("session_id")
    album_id = payload.get("album_id")

    # Required field validation
    missing = []
    if not code:
        missing.append("code")
    if not tier:
        missing.append("tier")
    if missing:
        return jsonify({"error": f"missing required field(s): {', '.join(missing)}"}), 400

    # Enum validation
    valid_tiers = {"mandatory", "recommended", "extra"}
    if tier not in valid_tiers:
        return jsonify({"error": f"invalid tier: {tier} (must be one of {sorted(valid_tiers)})"}), 400

    row = await _run(
        db_decisions.create_decision,
        code,
        tier,
        question,
        answer,
        rationale=rationale,
        source_doc=source_doc,
        session_id=session_id,
        album_id=album_id,
    )
    return jsonify(row), 201


# ============================================================
# Single-decision operations
# ============================================================

@decisions_bp.route("/api/decisions/<int:decision_id>", methods=["GET"])
async def get_decision(decision_id: int):
    """Fetch a decision by primary key."""
    row = await _run(db_decisions.get_decision_by_id, decision_id)
    if not row:
        return jsonify({"error": "decision not found"}), 404
    return jsonify(row)


@decisions_bp.route("/api/decisions/<int:decision_id>", methods=["PATCH"])
async def update_decision(decision_id: int):
    """Update a decision's answer, rationale, or source_doc.

    All three are optional — supply at least one. locked_at is bumped
    to the current time on any successful update.

    Distinguishing "field omitted" from "field explicitly null":
    - Field absent from payload → skip (no-op for that field)
    - Field present with value `null` → treat as "clear this field"
      (set to NULL in the db)
    - Field present with non-null value → update to that value

    Returns 404 if the decision doesn't exist.
    Returns 400 if no updatable fields are supplied at all (i.e. the
    payload was empty or every field was missing).
    """
    payload: Any = await request.get_json(silent=True) or {}

    # Sentinel distinguishes "key not present" from "key present with null".
    _MISSING = object()
    answer = payload.get("answer", _MISSING)
    rationale = payload.get("rationale", _MISSING)
    source_doc = payload.get("source_doc", _MISSING)

    has_answer = answer is not _MISSING
    has_rationale = rationale is not _MISSING
    has_source_doc = source_doc is not _MISSING

    if not (has_answer or has_rationale or has_source_doc):
        return jsonify({"error": "supply at least one of: answer, rationale, source_doc"}), 400

    # db layer accepts None as "set to NULL" (for explicit clears) and
    # treats absent keys as "don't touch" by passing a sentinel through.
    kwargs = {}
    if has_answer:
        kwargs["answer"] = answer  # may be None (clear) or string (update)
    if has_rationale:
        kwargs["rationale"] = rationale
    if has_source_doc:
        kwargs["source_doc"] = source_doc

    row = await _run(db_decisions.update_decision, decision_id, **kwargs)
    if not row:
        return jsonify({"error": "decision not found"}), 404
    return jsonify(row)


@decisions_bp.route("/api/decisions/<int:decision_id>", methods=["DELETE"])
async def delete_decision(decision_id: int):
    """Hard-delete a decision.

    Returns 204 on success.
    Returns 404 if the decision doesn't exist (already deleted).
    """
    ok = await _run(db_decisions.delete_decision, decision_id)
    if not ok:
        return jsonify({"error": "decision not found"}), 404
    return ("", 204)


# ============================================================
# Album / session scoped convenience
# ============================================================

@decisions_bp.route("/api/sessions/<session_id>/decisions", methods=["GET"])
async def list_session_decisions(session_id: str):
    """List all decisions captured during a given session."""
    rows = await _run(
        db_decisions.list_decisions,
        session_id=session_id,
    )
    return jsonify(rows)


@decisions_bp.route("/api/albums/<album_id>/decisions", methods=["GET"])
async def list_album_decisions(album_id: str):
    """List all decisions captured for an album (across all walks)."""
    rows = await _run(db_decisions.list_decisions, album_id=album_id)
    return jsonify(rows)
