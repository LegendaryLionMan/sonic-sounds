"""tests/test_sweepers.py — Day 8 sweeper tests.

Each sweeper tested in isolation with a fresh tempdb. Tests cover:
  - idle_pause.run_sweep: identifies & pauses idle sessions
  - wal_checkpoint.run_sweep: returns the 3-tuple shape
  - quota.run_sweep: graceful no-op when MCP+CLI both unavailable
  - mirror.run_sweep: copies new files, no-ops on matching md5
  - log_rotate.run_sweep: rotates at threshold, no-op otherwise
  - sweepers.start_all / stop_all: lifecycle
"""
import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _isolate_tempdb():
    tmpdir = Path(tempfile.mkdtemp(prefix="sonic-sounds-test-sweepers-"))
    tempdb = tmpdir / "test.db"
    os.environ["SONIC_SOUNDS_DB_PATH"] = str(tempdb)
    for mod_name in list(sys.modules):
        if mod_name == "db" or mod_name.startswith("db."):
            del sys.modules[mod_name]
    return tmpdir, tempdb


def _drop_isolation():
    from db.connection import close_all
    try:
        close_all()
    except Exception:
        pass
    for mod_name in list(sys.modules):
        if mod_name == "db" or mod_name.startswith("db."):
            del sys.modules[mod_name]
    os.environ.pop("SONIC_SOUNDS_DB_PATH", None)


class TestIdlePauseSweeper(unittest.IsolatedAsyncioTestCase):
    """sweepers/idle_pause — auto-pause sessions idle for 12h+."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir, cls.tempdb = _isolate_tempdb()
        from db import migrations, albums as db_albums, sessions as db_sessions
        migrations.bootstrap_initial_migration(cls.tempdb)
        migrations.run_migrations(cls.tempdb)
        db_albums.create_artist("a1", "A", db_path=cls.tempdb)
        for i in range(1, 6):
            db_albums.create_album(f"al{i}", f"Album {i}", "a1", db_path=cls.tempdb)
        cls.sessions = {}
        for i in range(1, 6):
            cls.sessions[i] = db_sessions.open_session(f"al{i}", db_path=cls.tempdb)

    @classmethod
    def tearDownClass(cls):
        _drop_isolation()
        import shutil
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    async def test_active_session_with_recent_activity_not_paused(self):
        """Fresh session (0h idle) is not paused."""
        from sweepers import idle_pause
        # Close any prior paused sessions to start clean
        from db.sessions import list_sessions, resume_session
        for s in (list_sessions(db_path=self.tempdb) or []):
            if s["status"] == "paused":
                resume_session(s["id"], db_path=self.tempdb)
        result = idle_pause.run_sweep(threshold_hours=12.0)
        self.assertEqual(result["paused"], 0)

    async def test_session_idle_past_threshold_is_paused(self):
        """Backdate last_activity_at to 13h ago, sweep with 12h threshold."""
        from sweepers import idle_pause
        from db import connection as db_conn
        from db import albums as db_albums, sessions as db_sessions
        # Create a fresh album + session so this test is fully isolated
        # from the others in this class.
        db_albums.create_album(f"al_backdate", "Backdate", "a1", db_path=self.tempdb)
        sess = db_sessions.open_session("al_backdate", db_path=self.tempdb)

        from datetime import datetime, timedelta, timezone
        thirteen_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=13)).strftime("%Y-%m-%d %H:%M:%S")
        conn = db_conn.open_db()
        try:
            conn.execute(
                "UPDATE album_sessions SET last_activity_at = ? WHERE id = ?",
                (thirteen_hours_ago, sess["id"]),
            )
            conn.commit()
        finally:
            db_conn.close_db()

        result = idle_pause.run_sweep(threshold_hours=12.0)
        self.assertGreaterEqual(result["paused"], 1)
        self.assertIn(sess["id"], result["paused_ids"])

    async def test_empty_session_list(self):
        """No active sessions → no errors, no pauses."""
        from db.sessions import pause_session, list_sessions, complete_session
        from sweepers import idle_pause
        # End ALL active sessions so the list is empty
        for s in (list_sessions(db_path=self.tempdb) or []):
            if s["status"] == "active":
                pause_session(s["id"], db_path=self.tempdb)
                complete_session(s["id"], db_path=self.tempdb)
        result = idle_pause.run_sweep(threshold_hours=12.0)
        self.assertEqual(result["candidates"], 0)
        self.assertEqual(result["paused"], 0)


class TestWalCheckpointSweeper(unittest.IsolatedAsyncioTestCase):
    """sweepers/wal_checkpoint — periodic WAL truncation."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir, cls.tempdb = _isolate_tempdb()
        from db import migrations
        migrations.bootstrap_initial_migration(cls.tempdb)
        migrations.run_migrations(cls.tempdb)

    @classmethod
    def tearDownClass(cls):
        _drop_isolation()
        import shutil
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    async def test_wal_checkpoint_returns_dict_shape(self):
        from sweepers import wal_checkpoint
        result = wal_checkpoint.run_sweep()
        # Per SQLite docs, wal_checkpoint returns (busy, log, checkpointed)
        self.assertIn("busy", result)
        self.assertIn("log", result)
        self.assertIn("checkpointed", result)
        self.assertEqual(result["mode"], "TRUNCATE")

    async def test_invalid_mode_raises(self):
        from sweepers import wal_checkpoint
        with self.assertRaises(ValueError):
            wal_checkpoint.run_sweep(mode="INVALID")


class TestQuotaSweeper(unittest.IsolatedAsyncioTestCase):
    """sweepers/quota — quota snapshot with graceful degradation."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir, cls.tempdb = _isolate_tempdb()
        from db import migrations
        migrations.bootstrap_initial_migration(cls.tempdb)
        migrations.run_migrations(cls.tempdb)

    @classmethod
    def tearDownClass(cls):
        _drop_isolation()
        import shutil
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    async def test_quota_source_unavailable_returns_error(self):
        """When neither MCP nor CLI is available, the sweeper reports
        error but doesn't crash the daemon."""
        from sweepers import quota
        with patch.object(quota, "_read_quota_via_mcp", return_value=None), \
             patch.object(quota, "_read_quota_via_cli", return_value=None):
            result = quota.run_sweep()
        self.assertFalse(result["ok"])
        self.assertIn("unavailable", result["error"])

    async def test_quota_snapshot_persists_to_db(self):
        """When MCP/CLI returns a dict, the snapshot persists 3 rows
        (general/video/speech) to quota_snapshots."""
        from sweepers import quota
        fake_quota = {
            "general_pct": 80,
            "video_pct": 90,
            "audio_pct": 50,
            "interval_remains_ms": 12345,
        }
        with patch.object(quota, "_read_quota_via_mcp", return_value=fake_quota), \
             patch.object(quota, "_read_quota_via_cli", return_value=None):
            result = quota.run_sweep()
        self.assertTrue(result["ok"])
        self.assertEqual(result["general_pct"], 80)
        self.assertEqual(result["video_pct"], 90)
        # Verify 3 rows landed (one per model_kind)
        import sqlite3
        conn = sqlite3.connect(str(self.tempdb))
        rows = conn.execute(
            "SELECT model_kind, interval_pct FROM quota_snapshots ORDER BY model_kind"
        ).fetchall()
        conn.close()
        self.assertEqual(len(rows), 3)
        kinds = {r[0]: r[1] for r in rows}
        self.assertEqual(kinds["general"], 80.0)
        self.assertEqual(kinds["video"], 90.0)
        self.assertEqual(kinds["speech"], 50.0)


class TestLogRotateSweeper(unittest.IsolatedAsyncioTestCase):
    """sweepers/log_rotate — size-based rotation at 10MB."""

    async def test_no_rotation_when_under_threshold(self):
        from sweepers import log_rotate
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False, mode="w") as f:
            f.write("small content\n")
            log_path = Path(f.name)
        try:
            result = log_rotate.run_sweep(log_path=log_path, max_bytes=1024)
            self.assertFalse(result["rotated"])
            # "small content\n" = 14 chars + 1 newline = 15 bytes
            self.assertEqual(result["size_before"], 15)
            self.assertTrue(log_path.exists())
        finally:
            log_path.unlink()

    async def test_rotation_at_threshold(self):
        from sweepers import log_rotate
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False, mode="w") as f:
            # Write 2KB of content
            f.write("x" * 2048)
            log_path = Path(f.name)
        try:
            result = log_rotate.run_sweep(log_path=log_path, max_bytes=1024)
            self.assertTrue(result["rotated"])
            self.assertEqual(result["size_before"], 2048)
            self.assertIsNotNone(result["backup_path"])
            # Original file should NOT exist (it was renamed)
            self.assertFalse(log_path.exists())
            # Backup should exist with the original content
            backup = Path(result["backup_path"])
            self.assertTrue(backup.exists())
            self.assertEqual(backup.stat().st_size, 2048)
        finally:
            if log_path.exists(): log_path.unlink()
            if Path(result["backup_path"]).exists():
                Path(result["backup_path"]).unlink()

    async def test_missing_log_file_is_noop(self):
        from sweepers import log_rotate
        result = log_rotate.run_sweep(log_path=Path("/tmp/does-not-exist-12345.log"))
        self.assertFalse(result["rotated"])
        self.assertIsNone(result["size_before"])


class TestMirrorSweeper(unittest.IsolatedAsyncioTestCase):
    """sweepers/mirror — file-tree mirror with md5 check."""

    async def test_copies_new_files(self):
        from sweepers import mirror
        with tempfile.TemporaryDirectory() as src_dir_str:
            with tempfile.TemporaryDirectory() as dst_dir_str:
                src_dir = Path(src_dir_str)
                dst_dir = Path(dst_dir_str)
                # Create a source file
                test_file = src_dir / "test.txt"
                test_file.write_text("hello mirror")
                result = mirror.run_sweep(source_dir=src_dir, mirror_dir=dst_dir)
                self.assertTrue(result["ok"])
                self.assertEqual(result["copied"], 1)
                self.assertEqual(result["up_to_date"], 0)
                # Mirror should have the file
                self.assertTrue((dst_dir / "test.txt").exists())
                self.assertEqual((dst_dir / "test.txt").read_text(), "hello mirror")

    async def test_skips_unchanged_files(self):
        from sweepers import mirror
        with tempfile.TemporaryDirectory() as src_dir_str:
            with tempfile.TemporaryDirectory() as dst_dir_str:
                src_dir = Path(src_dir_str)
                dst_dir = Path(dst_dir_str)
                (src_dir / "test.txt").write_text("same content")
                (dst_dir / "test.txt").write_text("same content")
                result = mirror.run_sweep(source_dir=src_dir, mirror_dir=dst_dir)
                self.assertEqual(result["up_to_date"], 1)
                self.assertEqual(result["copied"], 0)

    async def test_overwrites_changed_files(self):
        from sweepers import mirror
        with tempfile.TemporaryDirectory() as src_dir_str:
            with tempfile.TemporaryDirectory() as dst_dir_str:
                src_dir = Path(src_dir_str)
                dst_dir = Path(dst_dir_str)
                (src_dir / "test.txt").write_text("new content")
                (dst_dir / "test.txt").write_text("old content")
                result = mirror.run_sweep(source_dir=src_dir, mirror_dir=dst_dir)
                self.assertEqual(result["copied"], 1)
                self.assertEqual(result["up_to_date"], 0)
                self.assertEqual((dst_dir / "test.txt").read_text(), "new content")

    async def test_missing_source_is_ok(self):
        """No source dir = no artifacts yet = clean no-op."""
        from sweepers import mirror
        with tempfile.TemporaryDirectory() as dst_dir_str:
            result = mirror.run_sweep(
                source_dir=Path("/tmp/does-not-exist-source-9999"),
                mirror_dir=Path(dst_dir_str),
            )
            self.assertTrue(result["ok"])
            self.assertEqual(result["copied"], 0)


class TestSweepersLifecycle(unittest.IsolatedAsyncioTestCase):
    """sweepers.start_all / stop_all — the daemon's sweeper thread manager."""

    async def test_start_all_spawns_5_daemon_threads(self):
        from sweepers import start_all
        threads, stop_event = start_all()
        try:
            self.assertEqual(len(threads), 5)
            for t in threads:
                self.assertTrue(t.daemon)
                self.assertTrue(t.is_alive())
        finally:
            from sweepers import stop_all
            stop_all(threads, stop_event, timeout=2.0)

    async def test_stop_all_joins_within_timeout(self):
        from sweepers import start_all, stop_all
        threads, stop_event = start_all()
        # Sweeper intervals default to 60s+ — they're sleeping most of the time
        # so join should be near-instant.
        import time
        t0 = time.monotonic()
        stop_all(threads, stop_event, timeout=2.0)
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 2.5)
        for t in threads:
            self.assertFalse(t.is_alive())
