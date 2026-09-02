"""build/handlers_events.py — HTTP handlers for /api/events/*.

Day 5. Mirrors the structure of handlers_sessions.py:
- Async, all DB calls via asyncio.to_thread
- Same _run() wrapper (fresh connection per call, close on both sides)
- State machine: events are append-only (no transitions), but we still
  validate the session_id exists before allowing creates

Endpoints registered:
  GET    /api/events                       — list (filters: ?session=, ?since=, ?kind=, ?limit=)
  POST   /api/events                       — append an event (201/400)
  GET    /api/events/<event_id>            — get one (404)

The polling pattern is the day-1 deliverable: studio.js polls
/api/events?session=<id>&since=<ts> every 2s while session active,
30s idle (per Q34).
"""
import asyncio
import json as _json
from typing import Any

from quart import Blueprint, request, jsonify

from db import events as db_events
from db import connection as db_conn
from db import sessions as db_sessions


events_bp = Blueprint("events", __name__)


def _normalize(row):
    """Translate db/events.py row shape → HTTP response shape.

    - Rename `payload_json` → `payload` (parse JSON if non-null)
    - Return None if row is None so callers can use a simple truthy check.
    """
    if row is None:
        return None
    out = dict(row)
    if "payload_json" in out:
        raw = out.pop("payload_json")
        out["payload"] = _json.loads(raw) if raw else None
    return out


async def _run(fn, *args, **kwargs):
    """Offload a sync db call to a thread, with full open/close per call.

    Same rationale as in handlers_sessions.py — per-thread connection
    caching interacts badly with the async test runner's worker thread
    reuse, so we open/close a fresh connection per request.
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

@events_bp.route("/api/events", methods=["GET"])
async def list_events():
    """List events with optional filters.

    Query params (all optional):
      session: filter by session_id (required for sensible pagination)
      since: ISO timestamp; return only events created AFTER this
      since_id: integer event id; return only events with id > this
        (preferred for polling because id is monotonic — survives
        timestamp collisions at second precision)
      kind: filter by event kind ('chat' | 'build' | 'quota' | 'system' | 'log')
      limit: max rows to return (default 100, hard cap 500)
    """
    session_id = request.args.get("session")
    since_ts = request.args.get("since")
    since_id_raw = request.args.get("since_id")
    kind = request.args.get("kind")
    try:
        limit = min(int(request.args.get("limit", "100")), 500)
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400

    since_id = None
    if since_id_raw is not None:
        try:
            since_id = int(since_id_raw)
        except ValueError:
            return jsonify({"error": "since_id must be an integer"}), 400

    if not session_id:
        # Without a session filter, the query can be huge — reject to
        # prevent accidental full-table reads from the studio polling
        # loop. UI is supposed to scope by ?session=.
        return jsonify({"error": "session query param is required"}), 400

    rows = await _run(
        db_events.list_events,
        session_id,
        since_ts=since_ts,
        kind=kind,
        limit=limit,
    )
    # db_events.list_events doesn't know about since_id (it's a
    # session-row filter, not an id filter); apply the id predicate
    # post-hoc. We do this in the handler because the db layer's
    # pagination contract is by since_ts (per Q34) and we don't want
    # to break that signature.
    if since_id is not None:
        rows = [r for r in rows if r.get("id", 0) > since_id]
    return jsonify([_normalize(r) for r in rows])


@events_bp.route("/api/events", methods=["POST"])
async def create_event():
    """Append a new event to the log.

    Required fields: session_id, role, kind
    Optional: content, payload (dict), album_id, event_id (explicit)

    Returns 201 with the inserted event dict on success.
    Returns 400 if required fields are missing or role/kind are invalid.
    Returns 400 if the referenced session doesn't exist.
    """
    payload: Any = await request.get_json(silent=True) or {}

    session_id = payload.get("session_id")
    role = payload.get("role")
    kind = payload.get("kind")
    content = payload.get("content")
    event_payload = payload.get("payload")
    album_id = payload.get("album_id")
    event_id = payload.get("event_id")

    # Required field validation
    missing = []
    if not session_id:
        missing.append("session_id")
    if not role:
        missing.append("role")
    if not kind:
        missing.append("kind")
    if missing:
        return jsonify({"error": f"missing required field(s): {', '.join(missing)}"}), 400

    # Enum validation — match db/events.py docstring roles + kinds
    valid_roles = {"user", "assistant", "system", "tool"}
    valid_kinds = {"chat", "build", "quota", "system", "log"}
    if role not in valid_roles:
        return jsonify({"error": f"invalid role: {role} (must be one of {sorted(valid_roles)})"}), 400
    if kind not in valid_kinds:
        return jsonify({"error": f"invalid kind: {kind} (must be one of {sorted(valid_kinds)})"}), 400

    # Validate session exists — saves a dangling FK-less row we'd
    # otherwise have to garbage-collect.
    sess = await _run(db_sessions.get_session, session_id)
    if not sess:
        return jsonify({"error": f"session not found: {session_id}"}), 400

    event = await _run(
        db_events.create_event,
        session_id,
        role,
        kind,
        content,
        payload=event_payload,
        album_id=album_id,
        event_id=event_id,
    )
    return jsonify(_normalize(event)), 201


# ============================================================
# Single-event operations
# ============================================================

@events_bp.route("/api/events/<int:event_id>", methods=["GET"])
async def get_event(event_id: int):
    """Fetch a single event by primary key.

    Returns 404 if not found (rather than null body) so clients can
    distinguish a real miss from a partial response.
    """
    row = await _run(db_events.get_event, event_id)
    if not row:
        return jsonify({"error": "event not found"}), 404
    return jsonify(_normalize(row))


# ============================================================
# Session-scoped convenience
# ============================================================

@events_bp.route("/api/sessions/<session_id>/events", methods=["GET"])
async def list_session_events(session_id: str):
    """Same as /api/events?session=<id>, but expressed as a subresource.

    The studio page uses this URL shape; the bare /api/events stays
    available for tooling that wants to filter across sessions.
    """
    since_ts = request.args.get("since")
    since_id_raw = request.args.get("since_id")
    kind = request.args.get("kind")
    try:
        limit = min(int(request.args.get("limit", "100")), 500)
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400

    since_id = None
    if since_id_raw is not None:
        try:
            since_id = int(since_id_raw)
        except ValueError:
            return jsonify({"error": "since_id must be an integer"}), 400

    rows = await _run(
        db_events.list_events,
        session_id,
        since_ts=since_ts,
        kind=kind,
        limit=limit,
    )
    if since_id is not None:
        rows = [r for r in rows if r.get("id", 0) > since_id]
    return jsonify([_normalize(r) for r in rows])


@events_bp.route("/api/sessions/<session_id>/events/latest_id", methods=["GET"])
async def latest_session_event_id(session_id: str):
    """Return the highest event ID for a session — used by studio.js
    to compute the next `since` cursor without scanning all events.
    """
    eid = await _run(db_events.latest_event_id, session_id)
    if eid is None:
        return jsonify({"session_id": session_id, "latest_event_id": None}), 200
    return jsonify({"session_id": session_id, "latest_event_id": eid})
