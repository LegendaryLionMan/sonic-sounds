"""db/pipeline.py — pure read-side pipeline functions (per Phase 0.D).

Per PLAN-2026-07-28-v3.2 §Phase 0.D:
- Pure read-side functions, no mmx import
- can_run(layer_id, album_id) → bool
- next_runnable(album_id) → list of layer_ids
- mark_approved(layer_id, album_id) → bool (also a write — see below)

The pipeline is a 12-layer DAG declared in pipeline-deps.json. Each layer:
  {
    "id": "01_brief",
    "display_name": "Brief",
    "depends_on": [],
    "approval_required": false,
    "mmx_action": null | "<action_name>",
    "output_table": "album_briefs"
  }

build_jobs table tracks the per-album run-state:
  (album_id, layer_id, status, started_at, completed_at, approved_at, error)

status: "todo" | "running" | "done" | "blocked" | "needs_approval"
- A layer can_run if:
  1. Not already done/running for this album
  2. All dependencies are done for this album
  3. If approval_required: approved_at IS NOT NULL
  4. Not blocked (status != "blocked")
- next_runnable returns all can_run layers for an album, ordered by layer id.
- mark_approved flips the status from "needs_approval" → "ready to run".

The 12 layers (locked by plan §Q29c):
  01 brief · 02 lyrics_drafts · 03 lyrics_finalize · 04 vocal_recordings ·
  05 instrumental · 06 cover_art · 07 cassette_sticker · 08 audio_mastering ·
  09 metadata_isrc · 10 distribution · 11 press_kit · 12 finalize
"""
import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

# === Constants ===

# 12-layer DAG (locked by Q29c; declared in pipeline-deps.json but
# duplicated here for runtime use — single source of truth on disk).
PIPELINE_DEPS_FILE = Path(__file__).parent.parent / "pipeline-deps.json"

# Layer order (canonical — used to sort next_runnable)
LAYER_ORDER = [
    "01_brief",
    "02_lyrics_drafts",
    "03_lyrics_finalize",
    "04_vocal_recordings",
    "05_instrumental",
    "06_cover_art",
    "07_cassette_sticker",
    "08_audio_mastering",
    "09_metadata_isrc",
    "10_distribution",
    "11_press_kit",
    "12_finalize",
]

# Layers that require explicit user approval before running.
APPROVAL_REQUIRED = {
    "02_lyrics_drafts",   # user reviews generated lyrics
    "03_lyrics_finalize", # user finalizes before recording
    "06_cover_art",       # user picks from 4 cover variants
    "09_metadata_isrc",   # user reviews ISRC assignments
    "11_press_kit",       # user reviews before distribution
    "12_finalize",        # user finalizes the album
}


# === Internal helpers ===

def get_layer(layer_id: str) -> dict:
    """Public lookup of a single layer from pipeline-deps.json.

    Returns the layer dict with all 6 Q29c fields:
    {id, display_name, depends_on, approval_required, mmx_action, output_table}.

    Raises KeyError if the layer_id is unknown. The runner uses this
    to discover each layer mmx_action without reading the JSON
    directly (single source of truth: pipeline.py).
    """
    for layer in _load_pipeline_deps():
        if layer["id"] == layer_id:
            return layer
    raise KeyError(f"unknown layer_id: {layer_id!r}")


def _load_pipeline_deps() -> list[dict]:
    """Load the 12-layer DAG from pipeline-deps.json (single source of truth)."""
    with open(PIPELINE_DEPS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return data["days"][:12]  # First 12 are the pipeline days


def _connect(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection in WAL mode (per plan §Q24).
    Falls back to a default in-memory db if no path given.
    Sets row_factory so all results return dict-like rows.
    """
    conn = sqlite3.connect(db_path or ":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _row_to_job(row) -> dict:
    """Convert a build_jobs row to a dict.

    Handles both sqlite3.Row and tuple results (autocommit mode).
    """
    if not row:
        return {}
    if isinstance(row, dict):
        return row
    if isinstance(row, sqlite3.Row):
        return {k: row[k] for k in row.keys()}
    return dict(row)


# === Public API ===

def can_run(layer_id: str, album_id: str, db_path: str = "") -> bool:
    """Return True if `layer_id` can run for `album_id` right now.

    A layer can run if:
      1. No build_jobs row exists for (album_id, layer_id) with status
         "done" or "running".
      2. All dependencies in pipeline-deps.json are "done" for this album.
      3. If the layer is in APPROVAL_REQUIRED: the row is in status
         'ready' (after mark_approved) OR status 'needs_approval' with
         approved_at IS NOT NULL.
      4. Not blocked (no row with status "blocked" for this album/layer).

    Returns False otherwise. Pure read — does not write.
    """
    with _connect(db_path) as conn:
        # 1. Check the layer's own state
        row = conn.execute(
            "SELECT * FROM build_jobs WHERE album_id = ? AND layer_id = ?",
            (album_id, layer_id)
        ).fetchone()

        if row:
            row = _row_to_job(row)
            status = row.get("status")
            if status in ("done", "running", "blocked"):
                return False
            # 'ready' is the post-approval state and is runnable.
            # 'needs_approval' is runnable if approved_at is set
            # (older call sites may have stamped approved_at without
            # transitioning status — both paths are honored).
            if status == "needs_approval" and not row.get("approved_at"):
                return False

        # 2. Check dependencies
        deps = _get_dependencies(layer_id)
        for dep in deps:
            dep_row = conn.execute(
                "SELECT * FROM build_jobs WHERE album_id = ? AND layer_id = ?",
                (album_id, dep)
            ).fetchone()
            if not dep_row or dep_row["status"] != "done":
                return False

        # 3. Approval check for approval-required layers
        if layer_id in APPROVAL_REQUIRED and not row:
            # No job row → not even started → not approvable
            return False
        if layer_id in APPROVAL_REQUIRED and row and not row.get("approved_at"):
            return False

        return True


def next_runnable(album_id: str, db_path: str = "") -> list[str]:
    """Return the list of layer_ids that can run now for `album_id`.

    Ordered by LAYER_ORDER (canonical pipeline order). Pure read.
    """
    runnable = []
    for layer_id in LAYER_ORDER:
        if can_run(layer_id, album_id, db_path):
            runnable.append(layer_id)
    return runnable


def mark_approved(layer_id: str, album_id: str, db_path: str = "") -> bool:
    """Mark a layer as approved for the given album.

    Only meaningful for layers in APPROVAL_REQUIRED. Transitions the
    build_jobs row from 'needs_approval' -> 'ready' (and stamps approved_at).
    Returns True on success, False if no row exists or the layer is not
    approval-gated.

    The 'ready' status is now reachable through this code path (it was
    documented in the schema but unreachable previously). can_run() accepts
    both 'needs_approval' + approved_at AND 'ready' as runnable states.
    """
    if layer_id not in APPROVAL_REQUIRED:
        return False

    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM build_jobs WHERE album_id = ? AND layer_id = ?",
            (album_id, layer_id)
        ).fetchone()
        if not row:
            return False
        conn.execute(
            "UPDATE build_jobs SET approved_at = CURRENT_TIMESTAMP, status = 'ready' "
            "WHERE album_id = ? AND layer_id = ?",
            (album_id, layer_id)
        )
        conn.commit()
        return True


def _get_dependencies(layer_id: str) -> list[str]:
    """Return the list of layer_ids that `layer_id` depends on.

    Reads from pipeline-deps.json (per the plan: "each layer: id,
    display_name, depends_on[]"). Falls back to the canonical LAYER_ORDER
    (each layer depends on all prior layers) if the JSON file is missing
    the field.
    """
    try:
        deps_data = _load_pipeline_deps()
    except (FileNotFoundError, json.JSONDecodeError):
        return _infer_dependencies_from_order(layer_id)

    # pipeline-deps.json uses "day" for layer id; alias to "id"
    for layer in deps_data:
        if layer.get("id") == layer_id or layer.get("day") == layer_id:
            return layer.get("depends_on", [])
    return _infer_dependencies_from_order(layer_id)


def _infer_dependencies_from_order(layer_id: str) -> list[str]:
    """Fallback: infer deps from LAYER_ORDER (each layer depends on all
    prior layers). Used when pipeline-deps.json is missing or malformed.
    """
    if layer_id not in LAYER_ORDER:
        return []
    idx = LAYER_ORDER.index(layer_id)
    return LAYER_ORDER[:idx]


def layer_status(layer_id: str, album_id: str, db_path: str = "") -> str:
    """Return the current status of a layer for an album.

    Possible: "todo" (no row), "needs_approval" (gated, not approved),
    "ready" (gated, approved), "running", "done", "blocked".
    Pure read.
    """
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM build_jobs WHERE album_id = ? AND layer_id = ?",
            (album_id, layer_id)
        ).fetchone()
    if not row:
        return "todo"
    return row["status"]


def all_layers(album_id: str, db_path: str = "") -> list[dict]:
    """Return the status of all 12 layers for an album, in pipeline order.

    Output: [{layer_id, status, runnable}, ...]. Pure read.
    """
    out = []
    for layer_id in LAYER_ORDER:
        status = layer_status(layer_id, album_id, db_path)
        out.append({
            "layer_id": layer_id,
            "status": status,
            "runnable": can_run(layer_id, album_id, db_path),
        })
    return out
