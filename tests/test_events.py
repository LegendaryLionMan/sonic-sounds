"""tests/test_events.py — tests for db/events.py."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db import open_db, close_db, run_migrations
from db.events import create_event, list_events, get_event, latest_event_id, count_events, events_after
from db.albums import create_artist, create_album
from db.sessions import open_session


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


def _setup_session(db):
    """Helper: artist + album + session."""
    create_artist("a1", "Artist", db_path=db)
    create_album("a1", "Album", "a1", db_path=db)
    return open_session("a1", db_path=db)


class TestEvents(unittest.TestCase):
    def setUp(self):
        self.db = _fresh_db()
        self.session = _setup_session(self.db)

    def tearDown(self):
        _cleanup(self.db)

    def test_create_event(self):
        e = create_event(self.session["id"], "user", "chat",
                          "Hello world", db_path=self.db)
        self.assertIsNotNone(e["id"])
        self.assertEqual(e["role"], "user")
        self.assertEqual(e["content"], "Hello world")

    def test_create_event_with_payload(self):
        e = create_event(self.session["id"], "tool", "build",
                          "ran mmx music generate",
                          payload={"action": "music.generate", "duration": 180},
                          db_path=self.db)
        self.assertIn("music.generate", e["payload_json"])
        self.assertIn("duration", e["payload_json"])

    def test_list_events_all(self):
        for i in range(5):
            create_event(self.session["id"], "user", "chat", f"msg {i}",
                         db_path=self.db)
        events = list_events(self.session["id"], db_path=self.db)
        self.assertEqual(len(events), 5)

    def test_events_after_pagination(self):
        """Per Q34: pagination via ?since=<ts>."""
        import time
        for i in range(5):
            create_event(self.session["id"], "user", "chat", f"msg {i}",
                         db_path=self.db)
            time.sleep(1.05)  # ensure distinct 1-sec-resolution timestamps
        all_events = list_events(self.session["id"], db_path=self.db)
        # Pick a midpoint timestamp
        midpoint_ts = all_events[2]["created_at"]
        # Events AFTER the midpoint
        after = list_events(self.session["id"], since_ts=midpoint_ts, db_path=self.db)
        # The comparison is "created_at > midpoint_ts" — should give us 2 events
        # (those created strictly after midpoint)
        self.assertEqual(len(after), 2)
        for e in after:
            self.assertGreater(e["created_at"], midpoint_ts)

    def test_filter_by_kind(self):
        create_event(self.session["id"], "user", "chat", "hi", db_path=self.db)
        create_event(self.session["id"], "tool", "build", "build", db_path=self.db)
        create_event(self.session["id"], "tool", "build", "build 2", db_path=self.db)
        chat = list_events(self.session["id"], kind="chat", db_path=self.db)
        builds = list_events(self.session["id"], kind="build", db_path=self.db)
        self.assertEqual(len(chat), 1)
        self.assertEqual(len(builds), 2)

    def test_get_event(self):
        e = create_event(self.session["id"], "user", "chat", "msg", db_path=self.db)
        fetched = get_event(e["id"], db_path=self.db)
        self.assertEqual(fetched["content"], "msg")

    def test_latest_event_id(self):
        self.assertIsNone(latest_event_id(self.session["id"], db_path=self.db))
        e = create_event(self.session["id"], "user", "chat", "first", db_path=self.db)
        self.assertEqual(latest_event_id(self.session["id"], db_path=self.db), e["id"])
        e2 = create_event(self.session["id"], "user", "chat", "second", db_path=self.db)
        self.assertEqual(latest_event_id(self.session["id"], db_path=self.db), e2["id"])

    def test_count_events(self):
        for i in range(3):
            create_event(self.session["id"], "user", "chat", f"msg {i}", db_path=self.db)
        self.assertEqual(count_events(self.session["id"], db_path=self.db), 3)
        # filter by kind
        create_event(self.session["id"], "tool", "build", "b", db_path=self.db)
        self.assertEqual(count_events(self.session["id"], kind="chat", db_path=self.db), 3)
        self.assertEqual(count_events(self.session["id"], kind="build", db_path=self.db), 1)

    def test_events_after_convenience(self):
        for i in range(3):
            create_event(self.session["id"], "user", "chat", f"msg {i}", db_path=self.db)
        all_e = list_events(self.session["id"], db_path=self.db)
        midpoint = all_e[1]["created_at"]
        after = events_after(self.session["id"], since_ts=midpoint, db_path=self.db)
        for e in after:
            self.assertGreater(e["created_at"], midpoint)


if __name__ == "__main__":
    unittest.main()
