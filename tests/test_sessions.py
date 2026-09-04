"""tests/test_sessions.py — tests for db/sessions.py."""
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db import open_db, close_db, run_migrations
import db.sessions as sessions
from db.sessions import (
    open_session, pause_session, resume_session, complete_session,
    get_session, list_sessions, count_active_sessions, touch_activity,
    pause_idle_sessions, idle_hours, MAX_ACTIVE_SESSIONS, IDLE_THRESHOLD_HOURS,
)


def _fresh_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    result = run_migrations(path)
    assert len(result["errors"]) == 0
    return path


def _cleanup(path):
    """Close all cached connections and delete the test db.

    Uses close_all() (not close_db(path)) because tests may have
    cached conns to OTHER paths from previous operations in the same
    test. Leaving those open leaks file handles across the test suite
    on Windows (each leaked conn holds a WAL/SHM file lock).
    """
    from db.connection import close_all
    close_all()
    for ext in ["", "-journal", "-wal", "-shm"]:
        p = Path(path + ext)
        if p.exists():
            try:
                p.unlink()
            except OSError:
                pass


class TestSessionLifecycle(unittest.TestCase):
    def setUp(self):
        self.db = _fresh_db()
        # Need an album to create a session
        from db.albums import create_artist, create_album
        create_artist("maren-sol", "Maren Sol", db_path=self.db)
        create_album("a1", "Album 1", "maren-sol", db_path=self.db)

    def tearDown(self):
        _cleanup(self.db)

    def test_open_session(self):
        s = open_session("a1", db_path=self.db)
        self.assertIsNotNone(s)
        self.assertEqual(s["status"], "active")
        self.assertEqual(s["album_id"], "a1")
        self.assertIsNotNone(s["id"])
        self.assertIsNotNone(s["last_activity_at"])

    def test_pause_active(self):
        s = open_session("a1", db_path=self.db)
        paused = pause_session(s["id"], db_path=self.db)
        self.assertEqual(paused["status"], "paused")

    def test_cannot_pause_already_paused(self):
        s = open_session("a1", db_path=self.db)
        pause_session(s["id"], db_path=self.db)
        # Second pause should fail
        result = pause_session(s["id"], db_path=self.db)
        self.assertIsNone(result)

    def test_resume_paused(self):
        s = open_session("a1", db_path=self.db)
        pause_session(s["id"], db_path=self.db)
        resumed = resume_session(s["id"], db_path=self.db)
        self.assertEqual(resumed["status"], "active")

    def test_complete_session(self):
        s = open_session("a1", db_path=self.db)
        done = complete_session(s["id"], db_path=self.db)
        self.assertEqual(done["status"], "done")
        self.assertIsNotNone(done["closed_at"])

    def test_cannot_complete_already_done(self):
        s = open_session("a1", db_path=self.db)
        complete_session(s["id"], db_path=self.db)
        # Second complete should fail
        result = complete_session(s["id"], db_path=self.db)
        self.assertIsNone(result)

    def test_get_session_returns_none_for_missing(self):
        self.assertIsNone(get_session("nonexistent", db_path=self.db))


class TestMax3ActiveGuard(unittest.TestCase):
    def setUp(self):
        self.db = _fresh_db()
        from db.albums import create_artist, create_album
        create_artist("maren-sol", "Maren Sol", db_path=self.db)
        create_album("a1", "Album 1", "maren-sol", db_path=self.db)
        create_album("a2", "Album 2", "maren-sol", db_path=self.db)
        create_album("a3", "Album 3", "maren-sol", db_path=self.db)
        create_album("a4", "Album 4", "maren-sol", db_path=self.db)

    def tearDown(self):
        _cleanup(self.db)

    def test_max_3_active(self):
        """Per Q32: cannot have more than 3 active sessions."""
        self.assertEqual(MAX_ACTIVE_SESSIONS, 3)
        s1 = open_session("a1", db_path=self.db)
        s2 = open_session("a2", db_path=self.db)
        s3 = open_session("a3", db_path=self.db)
        self.assertIsNotNone(s1)
        self.assertIsNotNone(s2)
        self.assertIsNotNone(s3)
        # 4th should fail
        s4 = open_session("a4", db_path=self.db)
        self.assertIsNone(s4)
        self.assertEqual(count_active_sessions(db_path=self.db), 3)

    def test_pause_allows_new_session(self):
        s1 = open_session("a1", db_path=self.db)
        s2 = open_session("a2", db_path=self.db)
        s3 = open_session("a3", db_path=self.db)
        pause_session(s1["id"], db_path=self.db)
        # Now a 4th session should be allowed
        s4 = open_session("a4", db_path=self.db)
        self.assertIsNotNone(s4)
        self.assertEqual(count_active_sessions(db_path=self.db), 3)


class TestSessionQueries(unittest.TestCase):
    def setUp(self):
        self.db = _fresh_db()
        from db.albums import create_artist, create_album
        create_artist("maren-sol", "Maren Sol", db_path=self.db)
        create_album("a1", "Album 1", "maren-sol", db_path=self.db)
        create_album("a2", "Album 2", "maren-sol", db_path=self.db)

    def tearDown(self):
        _cleanup(self.db)

    def test_list_sessions_all(self):
        s1 = open_session("a1", db_path=self.db)
        s2 = open_session("a2", db_path=self.db)
        sessions_list = list_sessions(db_path=self.db)
        self.assertEqual(len(sessions_list), 2)

    def test_list_sessions_by_album(self):
        s1 = open_session("a1", db_path=self.db)
        s2 = open_session("a2", db_path=self.db)
        a1_sessions = list_sessions(album_id="a1", db_path=self.db)
        self.assertEqual(len(a1_sessions), 1)
        self.assertEqual(a1_sessions[0]["album_id"], "a1")

    def test_list_sessions_by_status(self):
        s1 = open_session("a1", db_path=self.db)
        s2 = open_session("a2", db_path=self.db)
        pause_session(s1["id"], db_path=self.db)
        paused = list_sessions(status="paused", db_path=self.db)
        self.assertEqual(len(paused), 1)
        active = list_sessions(status="active", db_path=self.db)
        self.assertEqual(len(active), 1)


class TestTouchActivity(unittest.TestCase):
    def setUp(self):
        self.db = _fresh_db()
        from db.albums import create_artist, create_album
        create_artist("maren-sol", "Maren Sol", db_path=self.db)
        create_album("a1", "Album 1", "maren-sol", db_path=self.db)

    def tearDown(self):
        _cleanup(self.db)

    def test_touch_updates_last_activity(self):
        s = open_session("a1", db_path=self.db)
        original_time = s["last_activity_at"]
        # Tiny sleep to ensure the timestamp moves (1 sec granularity)
        time.sleep(1.1)
        self.assertTrue(touch_activity(s["id"], db_path=self.db))
        updated = get_session(s["id"], db_path=self.db)
        self.assertNotEqual(updated["last_activity_at"], original_time)

    def test_touch_returns_false_for_missing(self):
        self.assertFalse(touch_activity("nonexistent", db_path=self.db))


class TestIdleSweeper(unittest.TestCase):
    def setUp(self):
        self.db = _fresh_db()
        from db.albums import create_artist, create_album
        create_artist("maren-sol", "Maren Sol", db_path=self.db)
        create_album("a1", "Album 1", "maren-sol", db_path=self.db)

    def tearDown(self):
        _cleanup(self.db)

    def test_idle_hours_calculation(self):
        s = open_session("a1", db_path=self.db)
        hours = idle_hours(s["id"], db_path=self.db)
        self.assertIsNotNone(hours)
        self.assertLess(hours, 0.1)  # just opened, ~0 hours

    def test_idle_sweeper_pauses_old_sessions(self):
        """Per Q32: 12h idle auto-pause."""
        s = open_session("a1", db_path=self.db)
        # Manually backdate last_activity_at to 13 hours ago
        conn = open_db(self.db)
        thirteen_hours_ago = (datetime.now(timezone.utc) -
                              timedelta(hours=13)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE album_sessions SET last_activity_at = ? WHERE id = ?",
            (thirteen_hours_ago, s["id"])
        )
        conn.commit()
        # Run the sweeper
        paused = pause_idle_sessions(db_path=self.db)
        self.assertEqual(len(paused), 1)
        # Verify the session is now paused
        updated = get_session(s["id"], db_path=self.db)
        self.assertEqual(updated["status"], "paused")

    def test_idle_sweeper_leaves_recent_sessions_alone(self):
        s = open_session("a1", db_path=self.db)
        # Don't backdate — should be < 12h old
        paused = pause_idle_sessions(db_path=self.db)
        self.assertEqual(len(paused), 0)

    def test_pause_idle_uses_parameterized_sql(self):
        """Regression: pause_idle_sessions used to build SQL with an
        f-string interpolating IDLE_THRESHOLD_HOURS. Now uses ? params
        so the SQL text is constant.
        """
        import inspect
        import re
        from db import sessions as sessions_mod
        src = inspect.getsource(sessions_mod.pause_idle_sessions)
        # Extract every triple-quoted string literal (the SQL templates).
        sql_blocks = re.findall(r'''"""(.*?)"""''', src, re.DOTALL)
        # The constant IDLE_THRESHOLD_HOURS may legitimately appear in an
        # f-string when computing the parameter value, but never inside
        # the SQL text itself.
        for sql in sql_blocks:
            self.assertNotIn(
                "{IDLE_THRESHOLD_HOURS", sql,
                f"SQL must not interpolate IDLE_THRESHOLD_HOURS: {sql!r}",
            )
            self.assertNotIn(
                "{cutoff}", sql,
                f"SQL must not interpolate cutoff: {sql!r}",
            )
        # Must use ? for the cutoff interval
        self.assertTrue(
            any("datetime('now', ?)" in sql for sql in sql_blocks),
            "pause_idle_sessions must pass cutoff as ? parameter to SQLite",
        )
        # Functional regression: the sweeper still pauses old sessions
        s = open_session("a1", db_path=self.db)
        conn = open_db(self.db)
        thirteen_hours_ago = (datetime.now(timezone.utc) -
                              timedelta(hours=13)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE album_sessions SET last_activity_at = ? WHERE id = ?",
            (thirteen_hours_ago, s["id"]),
        )
        conn.commit()
        paused = pause_idle_sessions(db_path=self.db)
        self.assertEqual(len(paused), 1)


if __name__ == "__main__":
    unittest.main()
