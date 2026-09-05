"""build/handlers_albums.py — HTTP handlers for /api/albums/* (Day 4).

Per PLAN-2026-08-09-v3.4 §Day 4:
- Albums CRUD endpoints, all async, all DB calls via asyncio.to_thread
- State transitions: create, update, archive, plus drilldowns (tracks,
  assets, sessions per album)

Endpoints registered:
  GET    /api/albums                — list (optional ?status=)
  POST   /api/albums                — create (201 on success, 400 on bad input)
  GET    /api/albums/<id>           — get one (404 if missing)
  PATCH  /api/albums/<id>           — partial update (404 if missing)
  POST   /api/albums/<id>/archive   — soft-delete (status='archived')
  GET    /api/albums/<id>/tracks    — list tracks for album
  GET    /api/albums/<id>/assets    — list assets (optional ?kind=)
  GET    /api/albums/<id>/sessions  — list sessions for album

Pattern (from Day 3 build/serve.py):
- All handlers async def
- All sync DB calls inside async handlers use asyncio.to_thread
- Validation errors → 400, missing row → 404, integrity conflicts → 409
- After each request the per-thread DB connection is closed via a
  finally block in _run(). This prevents the "database is locked" failure
  mode where a thread pool worker reuses a connection with a stale WAL
  write lock from a previous (failed) request.
"""
import asyncio
import logging
from typing import Any

from quart import Blueprint, request, jsonify

from db import albums as db_albums

_log = logging.getLogger("sonic_sounds.handlers.albums")


# Import db.connection lazily inside each function so per-test tempdb
# isolation (which re-imports db.* modules) is honored. Top-level
# `from db import ...` would freeze on the first import's function
# objects whose __globals__ reference the wrong module instance.
#
# Note: db_albums is imported at top because db.albums's CRUD functions
# don't depend on the live db path the way db.connection does — they
# all take an explicit db_path argument. So caching the module reference
# here is safe.


# Quart Blueprint lets us register a set of routes with one call.
# url_prefix is set at register time so tests can mount on a sub-path.
albums_bp = Blueprint("albums", __name__)


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
    from db import connection as db_conn
    def _wrapped():
        try:
            db_conn.close_db()  # Clear any cached conn from this thread
            return fn(*args, **kwargs)
        finally:
            db_conn.close_db()
    return await asyncio.to_thread(_wrapped)


def _required_fields(payload: dict, fields: list[str]) -> tuple[bool, str]:
    """Return (ok, missing_field_or_empty)."""
    for f in fields:
        if not payload.get(f):
            return False, f
    return True, ""


# ============================================================
# List + create
# ============================================================

@albums_bp.route("/api/albums", methods=["GET"])
async def list_albums():
    """List albums, optionally filtered by status.

    Each row is decorated with track_count (number of tracks in the
    album) so the library.js cassette wall can render "N tracks" in
    one round-trip. Backward-compatible — the row still has all the
    album-level fields.
    """
    status = request.args.get("status")
    rows = await _run(db_albums.list_albums, status=status)
    # Decorate with track_count from db.albums.list_tracks_count
    for r in rows:
        try:
            count = await _run(db_albums.list_tracks_count, r["id"])
        except Exception:
            count = None
        r["track_count"] = count
    return jsonify(rows)


@albums_bp.route("/api/albums", methods=["POST"])
async def create_album():
    payload: Any = await request.get_json(silent=True) or {}
    ok, missing = _required_fields(payload, ["id", "title", "primary_artist_id"])
    if not ok:
        return jsonify({"error": f"missing required field: {missing}"}), 400

    try:
        row = await _run(
            db_albums.create_album,
            payload["id"],
            payload["title"],
            payload["primary_artist_id"],
            status=payload.get("status", "active"),
            release_date=payload.get("release_date"),
            runtime_min=payload.get("runtime_min"),
            cover_path=payload.get("cover_path"),
            cassette_sticker_path=payload.get("cassette_sticker_path"),
            isrc=payload.get("isrc"),
            m09_sonic_dna=payload.get("m09_sonic_dna"),
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 409
    return jsonify(row), 201


# ============================================================
# Single-album operations
# ============================================================

@albums_bp.route("/api/albums/<album_id>", methods=["GET"])
async def get_album(album_id: str):
    row = await _run(db_albums.get_album, album_id)
    if not row:
        return jsonify({"error": "album not found"}), 404
    return jsonify(row)


@albums_bp.route("/api/albums/<album_id>", methods=["PATCH"])
async def update_album(album_id: str):
    payload: Any = await request.get_json(silent=True) or {}

    # Reject fields that PATCH shouldn't touch (id, created_at, etc).
    ALLOWED = {
        "title", "primary_artist_id", "status", "release_date",
        "runtime_min", "cover_path", "cassette_sticker_path",
        "isrc", "m09_sonic_dna",
    }
    clean = {k: v for k, v in payload.items() if k in ALLOWED}

    row = await _run(db_albums.update_album, album_id, **clean)
    if not row:
        return jsonify({"error": "album not found"}), 404
    return jsonify(row)


@albums_bp.route("/api/albums/<album_id>/archive", methods=["POST"])
async def archive_album(album_id: str):
    """Soft-delete: status → 'archived'. Returns 200 with the row, 404 if missing.

    Note: this calls db.albums.archive_album which delegates to update_album
    with status='archived'. Hard delete is intentionally not exposed via HTTP —
    use the CLI or the db layer directly.
    """
    row = await _run(db_albums.archive_album, album_id)
    if not row:
        return jsonify({"error": "album not found"}), 404
    return jsonify(row)


# ============================================================
# Day 11: finalize + reopen
# ============================================================

@albums_bp.route("/api/albums/<album_id>/finalize", methods=["POST"])
async def finalize_album_endpoint(album_id: str):
    """Day 11: finalize an album.

    Delegates to scripts.finalize_album.run_finalize(). Body params:
      target_lufs (default -14 = Spotify) — target integrated loudness
      true_peak_dbtp (default -1.0) — true-peak ceiling
      skip_mastering (default false) — skip ffmpeg loudnorm (dry-run)
      apply_id3 (default true) — write ID3 tags via mutagen

    Returns:
      200 {ok, lufs_measured, true_peak, mastered_files, id3_applied, album_status}
      404 if the album doesn't exist
      500 with error if mastering fails (album_status may still flip
      to 'done' if the album row write succeeded).
    """
    from scripts.finalize_album import run_finalize
    payload = await request.get_json(silent=True) or {}
    try:
        result = await asyncio.to_thread(
            run_finalize, album_id,
            target_lufs=float(payload.get("target_lufs", -14.0)),
            true_peak_dbtp=float(payload.get("true_peak_dbtp", -1.0)),
            skip_mastering=bool(payload.get("skip_mastering", False)),
            apply_id3=bool(payload.get("apply_id3", True)),
        )
        status_code = 200 if result.get("ok") else 500
        return jsonify(result), status_code
    except FileNotFoundError as e:
        return jsonify({"error": str(e), "ok": False}), 404
    except Exception as e:
        _log.exception(f"finalize failed for {album_id}")
        return jsonify({"error": f"{type(e).__name__}: {e}", "ok": False}), 500


@albums_bp.route("/api/albums/<album_id>/reopen", methods=["POST"])
async def reopen_album_endpoint(album_id: str):
    """Day 11: reopen a finalized album (status 'done' → 'active').

    Flips the album status back to 'active' so the studio can resume
    work on it. Does NOT undo mastering (mastered files stay in _master/).
    """
    row = await _run(db_albums.get_album, album_id)
    if not row:
        return jsonify({"error": "album not found"}), 404
    if row.get("status") not in ("done", "archived"):
        return jsonify({
            "error": f"album is in status {row['status']!r}; reopen only applies to done or archived",
            "current_status": row["status"],
        }), 409
    updated = await _run(db_albums.update_album, album_id, status="active")
    return jsonify(updated), 200


# ============================================================
# Drilldowns
# ============================================================

@albums_bp.route("/api/albums/<album_id>/tracks", methods=["GET"])
async def list_album_tracks(album_id: str):
    rows = await _run(db_albums.list_tracks, album_id)
    return jsonify(rows)


@albums_bp.route("/api/albums/<album_id>/assets", methods=["GET"])
async def list_album_assets(album_id: str):
    kind = request.args.get("kind")
    rows = await _run(db_albums.list_assets, album_id, kind=kind)
    return jsonify(rows)


@albums_bp.route("/api/albums/<album_id>/sessions", methods=["GET"])
async def list_album_sessions(album_id: str):
    # Lazy import to avoid circular dep with sessions handler.
    from db import sessions as db_sessions
    rows = await _run(db_sessions.list_sessions, album_id=album_id)
    return jsonify(rows)
