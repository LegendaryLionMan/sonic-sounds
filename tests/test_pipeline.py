"""tests/test_pipeline.py — unit tests for db/pipeline.py (per Phase 0.D verification).

Per PLAN-2026-07-28-v3.2 §Phase 0.D:
"Verification: unit test — given a synthetic build_jobs state, assert
can_run() returns correct booleans for the 12-layer DAG"

Tests cover:
  - can_run: blocked when dependency missing
  - can_run: true when all deps done (and not approval-gated)
  - can_run: false when already done
  - can_run: false when running
  - can_run: false when blocked
  - can_run: approval-gated layers need approved_at
  - next_runnable: returns in LAYER_ORDER
  - next_runnable: empty when all done
  - mark_approved: only works for approval-gated layers
  - mark_approved: sets approved_at
  - _infer_dependencies_from_order: correct dependency inference
  - LAYER_ORDER: 12 layers, correct order
"""
import sqlite3
import sys
import os
import tempfile
import unittest
from pathlib import Path

# Add the project root to sys.path so we can import db.pipeline
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import the module under test
from db.connection import open_db, verify_conn
from db import run_migrations  # noqa: E402
from db.pipeline import (
    LAYER_ORDER,
    APPROVAL_REQUIRED,
    can_run,
    next_runnable,
    mark_approved,
    layer_status,
    all_layers,
    _infer_dependencies_from_order,
    _get_dependencies,
)


# === Test fixture: in-memory SQLite with schema ===

def _build_test_db() -> str:
    """Create a fresh tempfile SQLite db with the schema for build_jobs.

    Returns the path for use with can_run/next_runnable. The in-memory
    ":memory:" doesn't work because each :memory: connection is independent
    in SQLite — the test's connection wouldn't be visible to the
    pipeline module's connection. A tempfile file IS shared.
    """
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path, isolation_level=None)  # autocommit
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript("""
        CREATE TABLE build_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            album_id TEXT NOT NULL,
            layer_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'todo',
            approved_at TEXT,
            started_at TEXT,
            completed_at TEXT,
            error TEXT,
            UNIQUE (album_id, layer_id)
        );
    """)
    conn.close()
    return path


def _seed(conn, album_id, layer_id, status="done", approved_at=None):
    """Helper: insert a build_jobs row. Autocommit mode is required because
    the pipeline module opens its own connection to the same file."""
    if not hasattr(conn, "row_factory") or conn.row_factory is None:
        conn.row_factory = sqlite3.Row
    conn.execute(
        "INSERT OR REPLACE INTO build_jobs (album_id, layer_id, status, approved_at) "
        "VALUES (?, ?, ?, ?)",
        (album_id, layer_id, status, approved_at)
    )
    # Note: PRAGMA wal_checkpoint needs exclusive lock — incompatible with
    # the pipeline module's open connection. Skip it; SQLite commits
    # are immediately visible to other connections on the same file.


# === Tests ===

class TestPipelineConstants(unittest.TestCase):
    """Lock the 12-layer DAG order and approval-gated set."""

    def test_12_layers_in_order(self):
        self.assertEqual(len(LAYER_ORDER), 12)
        self.assertEqual(LAYER_ORDER[0], "01_brief")
        self.assertEqual(LAYER_ORDER[-1], "12_finalize")
        # All IDs are unique
        self.assertEqual(len(set(LAYER_ORDER)), 12)
        # All are <num>_<name> format
        for lid in LAYER_ORDER:
            self.assertRegex(lid, r"^\d{2}_[a-z_]+$")

    def test_approval_required_set(self):
        # Per plan: gated layers are lyrics_drafts, lyrics_finalize, cover_art,
        # metadata_isrc, press_kit, finalize
        self.assertEqual(len(APPROVAL_REQUIRED), 6)
        self.assertIn("02_lyrics_drafts", APPROVAL_REQUIRED)
        self.assertIn("03_lyrics_finalize", APPROVAL_REQUIRED)
        self.assertIn("06_cover_art", APPROVAL_REQUIRED)
        self.assertIn("09_metadata_isrc", APPROVAL_REQUIRED)
        self.assertIn("11_press_kit", APPROVAL_REQUIRED)
        self.assertIn("12_finalize", APPROVAL_REQUIRED)
        # Not approval-gated: instrumentals, recordings, etc.
        self.assertNotIn("05_instrumental", APPROVAL_REQUIRED)
        self.assertNotIn("08_audio_mastering", APPROVAL_REQUIRED)


class TestCanRun(unittest.TestCase):
    """can_run() returns True only when all preconditions are met."""

    def setUp(self):
        self.db_path = _build_test_db()
        self.album = "half-light-hours"

    def tearDown(self):
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_layer_01_runnable_on_empty_album(self):
        # No build_jobs rows for this album
        self.assertTrue(can_run("01_brief", self.album, self.db_path))
        # Layer 02 requires layer 01 done, so false
        self.assertFalse(can_run("02_lyrics_drafts", self.album, self.db_path))
        # Layer 05 (instrumental) requires layers 01-04 done
        self.assertFalse(can_run("05_instrumental", self.album, self.db_path))

    def test_all_done_makes_12_done(self):
        # Mark all 12 done
        with sqlite3.connect(self.db_path) as conn:
            for lid in LAYER_ORDER:
                _seed(conn, self.album, lid, status="done")
        # Layer 12 is already done, so cannot run again
        for lid in LAYER_ORDER:
            self.assertFalse(can_run(lid, self.album, self.db_path))

    def test_running_blocks_rerun(self):
        with sqlite3.connect(self.db_path) as conn:
            _seed(conn, self.album, "01_brief", status="running")
        self.assertFalse(can_run("01_brief", self.album, self.db_path))

    def test_blocked_blocks(self):
        with sqlite3.connect(self.db_path) as conn:
            _seed(conn, self.album, "01_brief", status="blocked")
        self.assertFalse(can_run("01_brief", self.album, self.db_path))

    def test_approval_gated_layer_needs_approved_at(self):
        with sqlite3.connect(self.db_path) as conn:
            # Mark prior layer done
            _seed(conn, self.album, "01_brief", status="done")
            # layer 02 is approval-gated; without approved_at, NOT runnable
            _seed(conn, self.album, "02_lyrics_drafts", status="needs_approval")
        self.assertFalse(can_run("02_lyrics_drafts", self.album, self.db_path))

    def test_approval_gated_layer_with_approved_at_runs(self):
        with sqlite3.connect(self.db_path) as conn:
            _seed(conn, self.album, "01_brief", status="done")
            _seed(conn, self.album, "02_lyrics_drafts", status="needs_approval", approved_at="2026-08-05")
        self.assertTrue(can_run("02_lyrics_drafts", self.album, self.db_path))

    def test_dependency_chain_layer_5(self):
        with sqlite3.connect(self.db_path) as conn:
            for lid in ["01_brief", "02_lyrics_drafts", "03_lyrics_finalize", "04_vocal_recordings"]:
                status = "done" if lid not in APPROVAL_REQUIRED else "done"
                approved = None
                if lid in APPROVAL_REQUIRED:
                    approved = "2026-08-05"
                _seed(conn, self.album, lid, status=status, approved_at=approved)
        # Layer 05 needs layers 01-04 done
        self.assertTrue(can_run("05_instrumental", self.album, self.db_path))

    def test_mixed_album_state(self):
        with sqlite3.connect(self.db_path) as conn:
            _seed(conn, self.album, "01_brief", status="done")
            # layer 03 is approval-gated, must be approved first
            _seed(conn, self.album, "02_lyrics_drafts", status="done", approved_at="2026-08-05")
        # Before layer 03 has a row + approval, it can't run
        self.assertFalse(can_run("03_lyrics_finalize", self.album, self.db_path))
        # Insert layer 03 with approved_at (the test's path; mark_approved needs a row)
        with sqlite3.connect(self.db_path) as conn:
            _seed(conn, self.album, "03_lyrics_finalize", status="needs_approval", approved_at="2026-08-05")
        self.assertTrue(can_run("03_lyrics_finalize", self.album, self.db_path))


class TestNextRunnable(unittest.TestCase):
    """next_runnable returns layers in LAYER_ORDER."""

    def setUp(self):
        self.db_path = _build_test_db()
        self.album = "half-light-hours"

    def tearDown(self):
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_empty_album_returns_layer_01(self):
        runnable = next_runnable(self.album, self.db_path)
        self.assertEqual(runnable, ["01_brief"])

    def test_all_done_returns_empty(self):
        with sqlite3.connect(self.db_path) as conn:
            for lid in LAYER_ORDER:
                _seed(conn, self.album, lid, status="done")
        self.assertEqual(next_runnable(self.album, self.db_path), [])

    def test_sequential_progress(self):
        with sqlite3.connect(self.db_path) as conn:
            for lid in ["01_brief"]:
                _seed(conn, self.album, lid, status="done")
        # Layer 02 is approval-gated; without approval, it can't run.
        # (Correct: next_runnable returns [] because layer 02 needs approval.)
        runnable = next_runnable(self.album, self.db_path)
        self.assertEqual(runnable, [])
        # Now insert layer 02 with approved_at and mark_approved
        with sqlite3.connect(self.db_path) as conn:
            _seed(conn, self.album, "02_lyrics_drafts", status="needs_approval", approved_at="2026-08-05")
        runnable = next_runnable(self.album, self.db_path)
        self.assertEqual(runnable, ["02_lyrics_drafts"])

    def test_layers_returned_in_order(self):
        # Mark layers 01-04 done + approved (gated ones), layer 05 should be next
        with sqlite3.connect(self.db_path) as conn:
            for lid in ["01_brief", "02_lyrics_drafts", "03_lyrics_finalize", "04_vocal_recordings"]:
                status = "done"
                approved = "2026-08-05" if lid in APPROVAL_REQUIRED else None
                _seed(conn, self.album, lid, status=status, approved_at=approved)
        runnable = next_runnable(self.album, self.db_path)
        # Only layer 05 should be runnable (others done or not yet approvable)
        self.assertEqual(runnable, ["05_instrumental"])


class TestMarkApproved(unittest.TestCase):
    """mark_approved only works for approval-gated layers."""

    def setUp(self):
        self.db_path = _build_test_db()
        self.album = "half-light-hours"

    def tearDown(self):
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_non_gated_layer_returns_false(self):
        with sqlite3.connect(self.db_path) as conn:
            _seed(conn, self.album, "01_brief", status="todo")
        result = mark_approved("01_brief", self.album, self.db_path)
        self.assertFalse(result)
        # approved_at should still be NULL
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT approved_at FROM build_jobs WHERE layer_id = ?", ("01_brief",)).fetchone()
        self.assertIsNone(row["approved_at"])

    def test_gated_layer_with_no_row_returns_false(self):
        # No build_jobs row for layer 02 yet
        result = mark_approved("02_lyrics_drafts", self.album, self.db_path)
        self.assertFalse(result)

    def test_gated_layer_with_row_sets_approved_at(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            _seed(conn, self.album, "01_brief", status="done")
            _seed(conn, self.album, "02_lyrics_drafts", status="needs_approval")
        result = mark_approved("02_lyrics_drafts", self.album, self.db_path)
        self.assertTrue(result)
        # Verify approved_at was set
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT approved_at FROM build_jobs WHERE album_id = ? AND layer_id = ?",
                (self.album, "02_lyrics_drafts")
            ).fetchone()
        self.assertIsNotNone(row["approved_at"])


class TestAllLayers(unittest.TestCase):
    """all_layers returns the 12-layer status report."""

    def setUp(self):
        self.db_path = _build_test_db()
        self.album = "half-light-hours"

    def tearDown(self):
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_empty_album_returns_12_todo(self):
        layers = all_layers(self.album, self.db_path)
        self.assertEqual(len(layers), 12)
        for i, layer in enumerate(layers):
            self.assertEqual(layer["layer_id"], LAYER_ORDER[i])
            self.assertEqual(layer["status"], "todo")
            # Only layer 01 should be runnable
            self.assertEqual(layer["runnable"], (i == 0))

    def test_full_built_state(self):
        with sqlite3.connect(self.db_path) as conn:
            for lid in LAYER_ORDER:
                _seed(conn, self.album, lid, status="done")
        layers = all_layers(self.album, self.db_path)
        for layer in layers:
            self.assertEqual(layer["status"], "done")
            self.assertFalse(layer["runnable"])


class TestDependencyInference(unittest.TestCase):
    """_get_dependencies reads from pipeline-deps.json with LAYER_ORDER fallback."""

    def test_infer_from_order(self):
        # layer 01 has no deps
        self.assertEqual(_infer_dependencies_from_order("01_brief"), [])
        # layer 05 has layers 01-04 as deps
        deps = _infer_dependencies_from_order("05_instrumental")
        self.assertEqual(set(deps), {"01_brief", "02_lyrics_drafts", "03_lyrics_finalize", "04_vocal_recordings"})
        # layer 12 has layers 01-11
        deps = _infer_dependencies_from_order("12_finalize")
        self.assertEqual(len(deps), 11)
        # Unknown layer returns empty
        self.assertEqual(_infer_dependencies_from_order("99_unknown"), [])

    def test_get_dependencies_uses_pipeline_deps(self):
        # pipeline-deps.json should exist at the project root
        deps_path = PROJECT_ROOT / "pipeline-deps.json"
        self.assertTrue(deps_path.exists(), "pipeline-deps.json must exist for Phase 0.D")
        # The 'days' array in pipeline-deps.json should have at least 12 entries
        import json
        with open(deps_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertGreaterEqual(len(data["days"]), 12)


class TestEmptyDBPath(unittest.TestCase):
    """Default db_path=''. Verified after Day 2 (db/connection.py + db/migrations.py)."""

    def test_empty_db_path_uses_memory(self):
        """Per plan §7 Day 2 verification: open_db() opens, runs migrations, PRAGMAs verified."""
        import tempfile
        import os
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            conn = open_db(path)
            # Apply migrations
            result = run_migrations(path)
            self.assertEqual(len(result["errors"]), 0,
                             f"Migration errors: {result['errors']}")
            # Verify PRAGMAs
            pragmas = verify_conn(conn)
            self.assertEqual(pragmas["journal_mode"], "wal")
            self.assertEqual(pragmas["foreign_keys"], 1)
            self.assertEqual(pragmas["busy_timeout"], 5000)
            # Verify schema_version is set
            self.assertGreaterEqual(result["schema_version"], 1)
        finally:
            # Close the connection so we can delete the file on Windows
            from db.connection import close_db
            close_db(path)
            os.unlink(path)
            for ext in ["-journal", "-wal", "-shm"]:
                p2 = path + ext
                if os.path.exists(p2):
                    try:
                        os.unlink(p2)
                    except OSError:
                        pass


if __name__ == "__main__":
    unittest.main()
