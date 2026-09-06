"""build/handlers_intake.py - HTTP intake submit endpoint (Day 9).

Per plan section Day 9:
  "site/intake.html: 21-question intake, one field at a time, answer-first"
  "handlers/intake.py: submit (validates against Q8 schema, creates
   album + first session)"
  "brief-builder.html: assembles intake JSON into the locked
   concept-brief template"

This handler implements the SUBMIT side. The intake.html page
already exists (Editorial Zine era) — it POSTs a FormData body
containing 26 question fields (M01-M09, R09-R14, E15-E21).

Public API:
  POST /api/intake/submit
    Body: FormData with 26 fields + album_id (optional).
           OR JSON body: {album_id, questions: {qid: value}, sonic_dna?}
    Returns 200 with {brief_id, validation_errors, album_id, session_id}.
    Creates album + session if not provided.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Optional

from quart import Blueprint, request, jsonify

import db.album_briefs as db_briefs
import db.albums as db_albums
import db.sessions as db_sessions
import db.decisions as db_decisions

_log = logging.getLogger("sonic_sounds.intake")

# Per intake.html data-qid attributes (verified 2026-09-02).
# Used to extract the right fields from FormData and validate completeness.
INTAKE_MANDATORY_QUESTIONS = [
    "M01_concept", "M02_scope", "M03_genre", "M04_references",
    "M05_vocal", "M06_language", "M07_runtime", "M08_artist",
    "M09_sonicDNA",
]


intake_bp = Blueprint("intake", __name__)


async def _run(fn, *args, **kwargs):
    """Offload sync db calls to a thread."""
    def _wrapped():
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            _log.exception(f"intake db call failed: {e}")
            raise
    return await asyncio.to_thread(_wrapped)


def _extract_form_to_questions(form: dict) -> dict:
    """Map FormData fields to a {qid: value} dict.

    intake.html uses `name="M01_concept"`, `name="M02_scope"`, etc. Multi-
    value questions like M04_references use name="M04_ref1/2/3".

    Per CATCH-UP 2026-09-05 audit (#13): the JSON path now ALSO collapses
    M04_ref1/2/3 — previously, a JSON submission with M04_ref1=... would
    stay as M04_ref1, while a FormData submission would collapse to
    M04_references, producing two different brief_json shapes for the
    same answer. The collapsed M04_references list is the canonical
    shape per db/album_briefs.py MANDATORY_M_QUESTIONS.
    """
    questions: dict[str, Any] = {}
    for key, value in form.items():
        if not value or (isinstance(value, str) and not value.strip()):
            continue
        # Reference trio: collapse M04_ref1, M04_ref2, M04_ref3 into M04_references
        if key.startswith("M04_ref"):
            questions.setdefault("M04_references", []).append(value)
            continue
        questions[key] = value
    # Always include the question ids even if empty (so the brief JSON has
    # stable shape)
    return questions


def _normalize_json_to_questions(payload: dict) -> dict:
    """Apply the same form-side normalizations to a JSON payload.

    JSON callers sometimes send M04_ref1/M04_ref2/M04_ref3 as separate
    keys (mirroring the form) instead of a single M04_references list.
    Collapse those into M04_references so both paths produce identical
    brief_json shapes.
    """
    if not isinstance(payload, dict):
        return {}
    out = dict(payload)
    refs = []
    for k in ("M04_ref1", "M04_ref2", "M04_ref3"):
        v = out.pop(k, None)
        if isinstance(v, str) and v.strip():
            refs.append(v)
        elif isinstance(v, list):
            refs.extend(x for x in v if x)
    if refs and "M04_references" not in out:
        out["M04_references"] = refs
    return out


def _extract_m09_sonic_dna(questions: dict) -> Optional[dict]:
    """Parse the M09_sonicDNA field as JSON if user supplied it.

    intake.html renders M09 as a textarea where the user is supposed to
    paste a sonic-dna JSON (matching the m09_sonic_dna column on albums).
    Best-effort parse: returns None if the field isn't valid JSON.
    """
    import json
    raw = questions.get("M09_sonicDNA")
    if not raw:
        return None
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


@intake_bp.route("/api/intake/submit", methods=["POST"])
async def submit_intake():
    """Accept intake form submission, validate, persist brief.

    Accepts both FormData (intake.html form submit) and JSON (programmatic).
    Creates the album + first session if album_id is not provided.

    Body (FormData or JSON):
      - album_id: optional existing album slug. If absent, a new album
        is created using album_title (from R09_title) + artist (from
        M08_artist). Album slug is derived from R09_title.
      - questions: dict of qid -> value (extracted from FormData or
        supplied directly in JSON).
      - sonic_dna: optional dict (M09 JSON parsed).

    Returns 200 with:
      {brief_id, album_id, session_id, validation_errors, locked_qids}.
    Returns 400 if validation fails (M-tier questions all missing).
    """
    # Accept both Content-Types. FormData for the existing HTML form;
    # JSON for programmatic / API clients.
    ctype = request.headers.get("Content-Type", "").lower()
    payload: dict = {}
    if "application/json" in ctype:
        payload = await request.get_json(silent=True) or {}
        # Per audit #13: normalize the JSON payload the same way the
        # FormData path does (collapse M04_ref1/2/3 -> M04_references).
        questions = _normalize_json_to_questions(payload.get("questions", {}))
        album_id = payload.get("album_id")
        artist_id = payload.get("artist_id") or payload.get("primary_artist_id")
        sonic_dna = _extract_m09_sonic_dna(questions)
    else:
        form = await request.form
        album_id = form.get("album_id")
        artist_id = form.get("primary_artist_id") or form.get("artist_id")
        questions = _extract_form_to_questions(dict(form))
        sonic_dna = _extract_m09_sonic_dna(questions)

    # Build the brief payload
    brief_payload = {
        "questions": questions,
        "sonic_dna": sonic_dna,
        "version": "v1",  # locked concept-brief template version
    }

    # Validate
    validation_errors = db_briefs.validate_brief_payload(brief_payload)

    # Album + session bootstrap if needed
    # Derive album_id from R09_title if not provided.
    title_for_album = questions.get("R09_title") or questions.get("M01_concept")
    if not album_id:
        if not title_for_album or not str(title_for_album).strip():
            return jsonify({
                "error": "album_id is required OR R09_title (album title) must be non-empty",
                "validation_errors": validation_errors,
            }), 400
        # Slugify the title
        slug = "".join(c.lower() if c.isalnum() else "-" for c in str(title_for_album)[:64]).strip("-")
        if not slug:
            return jsonify({
                "error": "album_id is required OR R09_title (album title) must be non-empty",
                "validation_errors": validation_errors,
            }), 400
        album_id = slug
    # From here, album_id is always set. Artist is required to create
    # the album row (FK constraint).
    if not artist_id:
        return jsonify({
            "error": "primary_artist_id is required",
            "validation_errors": validation_errors,
        }), 400

    # Runtime_min from M07 if available, else 0.
    runtime_min = 0
    try:
        runtime_min = int(str(questions.get("M07_runtime", "0")).strip() or 0)
    except (ValueError, TypeError):
        runtime_min = 0

    # Ensure the artist exists. Per the 2026-09-06 advanced E2E audit,
    # we previously hit a UNIQUE constraint failed on artists.name when
    # the auto-defaulted artist_id matched the name of an existing
    # artist. Reuse existing artist by name when M08_artist matches
    # one already in the table.
    existing_artist = await _run(db_albums.get_artist, artist_id)
    if existing_artist is None:
        requested_name = (
            questions.get("M08_artist")
            or artist_id.replace("-", " ").title()
        )
        # Check if any artist already has this name; reuse it under the
        # caller-supplied artist_id by skipping the create. If not,
        # create fresh.
        all_artists = await _run(db_albums.list_artists)
        name_match = next(
            (a for a in (all_artists or []) if a.get("name") == requested_name),
            None,
        )
        if name_match is not None:
            # Reuse the existing artist's id; update the album's
            # primary_artist_id accordingly.
            artist_id = name_match["id"]
        else:
            try:
                await _run(db_albums.create_artist, artist_id, requested_name)
            except (ValueError, sqlite3.IntegrityError) as e:
                _log.info(f"artist {artist_id} already exists, reusing: {e}")

    # Ensure the album exists. Per the 2026-09-06 advanced E2E audit:
    # when the caller supplies album_id, we previously skipped the
    # create-album branch and crashed with FOREIGN KEY constraint
    # failed when upsert_brief tried to insert the brief against a
    # non-existent album. Now we always ensure the album exists.
    existing_album = await _run(db_albums.get_album, album_id)
    if existing_album is None:
        album_title = str(title_for_album or album_id).strip() or album_id
        try:
            await _run(db_albums.create_album, album_id, album_title, artist_id,
                       runtime_min=runtime_min)
        except (ValueError, sqlite3.IntegrityError) as e:
            _log.info(f"album {album_id} already exists, reusing: {e}")

    # Persist the brief
    row = await _run(
        db_briefs.upsert_brief, album_id, brief_payload, sonic_dna=sonic_dna,
    )

    # Open a session for the new album so the studio is ready
    session_id = None
    try:
        session = await _run(db_sessions.open_session, album_id)
        session_id = session["id"]
    except Exception as e:
        _log.warning(f"could not open session for {album_id}: {e}")

    return jsonify({
        "ok": True,
        "brief_id": album_id,
        "album_id": album_id,
        "session_id": session_id,
        "validation_errors": validation_errors,
        "locked_qids": sorted(db_briefs.MANDATORY_M_QUESTIONS),
    }), 200


@intake_bp.route("/api/intake/brief/<album_id>", methods=["GET"])
async def get_brief_endpoint(album_id: str):
    """Return the persisted brief for an album."""
    row = await _run(db_briefs.get_brief, album_id)
    if row is None:
        return jsonify({"error": f"no brief for album {album_id!r}"}), 404
    # The brief JSON is parsed into `brief` key by get_brief; keep that
    return jsonify(row), 200


@intake_bp.route("/api/intake/briefs", methods=["GET"])
async def list_briefs_endpoint():
    """List all briefs (most recent first)."""
    rows = await _run(db_briefs.list_briefs)
    return jsonify(rows), 200
