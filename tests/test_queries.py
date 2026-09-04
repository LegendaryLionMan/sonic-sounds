"""tests/test_queries.py — tests for db/queries.py."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db import open_db, close_db, run_migrations
from db.albums import create_artist, create_album
from db.sessions import open_session
from db.build_jobs import queue_job, mark_succeeded
from db.events import create_event
from db.queries import (
    dashboard_summary, recent_albums_with_progress, session_chat_history,
    build_jobs_for_album, global_status, format_status_4line,
)


def _fresh_db():
    from db.connection import close_all
    close_all()
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    result = run_migrations(path)
    assert len(result["errors"]) == 0
    return path


def _cleanup(path):
    from db.connection import close_all
    close_all()
    for ext in ["", "-journal", "-wal", "-shm"]:
        p = Path(path + ext)
        if p.exists():
            try:
                p.unlink()
            except OSError:
                pass


def _setup_album(db, slug="a1", title="Album 1", artist="a1"):
    create_artist(artist, f"Artist {artist}", db_path=db)
    create_album(slug, title, artist, db_path=db)


class TestQueries(unittest.TestCase):
    def setUp(self):
        self.db = _fresh_db()
        _setup_album(self.db)

    def tearDown(self):
        _cleanup(self.db)

    def test_dashboard_summary(self):
        s = open_session("a1", db_path=self.db)
        create_event(s["id"], "user", "chat", "hello", db_path=self.db)
        # Queue some jobs
        queue_job("a1", "01_brief", db_path=self.db)
        queue_job("a1", "02_lyrics_drafts", db_path=self.db)

        summary = dashboard_summary("a1", db_path=self.db)
        self.assertEqual(summary["album"]["id"], "a1")
        self.assertEqual(len(summary["sessions"]), 1)
        self.assertEqual(summary["sessions"][0]["status"], "active")
        self.assertEqual(len(summary["jobs"]), 2)
        self.assertEqual(len(summary["tracks"]), 0)

    def test_dashboard_summary_missing_album(self):
        summary = dashboard_summary("nonexistent", db_path=self.db)
        self.assertEqual(summary, {})

    def test_recent_albums_with_progress(self):
        _setup_album(self.db, slug="a2", title="Album 2", artist="a2")
        # Album 1 has 1 of 2 jobs done
        queue_job("a1", "01_brief", db_path=self.db)
        j2 = queue_job("a1", "02_lyrics_drafts", db_path=self.db)
        mark_succeeded(j2["id"], db_path=self.db)
        # Album 2 has 0 jobs
        recent = recent_albums_with_progress(limit=10, db_path=self.db)
        self.assertEqual(len(recent), 2)
        a1 = next(a for a in recent if a["id"] == "a1")
        self.assertEqual(a1["total_jobs"], 2)
        self.assertEqual(a1["done_jobs"], 1)
        self.assertEqual(a1["progress"], 0.5)
        a2 = next(a for a in recent if a["id"] == "a2")
        self.assertEqual(a2["total_jobs"], 0)
        self.assertEqual(a2["progress"], 0.0)

    def test_session_chat_history(self):
        s = open_session("a1", db_path=self.db)
        for i in range(5):
            create_event(s["id"], "user", "chat", f"msg {i}", db_path=self.db)
        history = session_chat_history(s["id"], limit=10, db_path=self.db)
        # Returns DESC order
        self.assertEqual(len(history), 5)
        self.assertEqual(history[0]["content"], "msg 4")  # most recent first

    def test_build_jobs_for_album(self):
        queue_job("a1", "01_brief", db_path=self.db)
        queue_job("a1", "02_lyrics_drafts", db_path=self.db)
        queue_job("a1", "03_lyrics_finalize", db_path=self.db)
        jobs = build_jobs_for_album("a1", db_path=self.db)
        self.assertEqual(len(jobs["todo"]), 3)
        self.assertNotIn("done", jobs)

    def test_global_status(self):
        s = open_session("a1", db_path=self.db)
        status = global_status(db_path=self.db)
        self.assertEqual(status["active_sessions"], 1)
        self.assertEqual(status["paused_sessions"], 0)
        self.assertEqual(status["total_albums"], 1)
        self.assertEqual(status["done_albums"], 0)
        self.assertEqual(status["total_tracks"], 0)

    def test_format_status_4line(self):
        status = {
            "active_sessions": 2,
            "paused_sessions": 1,
            "done_albums": 3,
            "total_albums": 5,
            "quota_remaining": {"general": 73, "video": 88},
        }
        formatted = format_status_4line(status)
        lines = formatted.split("\n")
        self.assertEqual(len(lines), 4)
        self.assertIn("active sessions: 2/3", lines[0])
        self.assertIn("paused: 1", lines[1])
        self.assertIn("done albums: 3/5", lines[2])
        self.assertIn("quota remaining: general 73", lines[3])
        self.assertIn("video 88", lines[3])


if __name__ == "__main__":
    unittest.main()
