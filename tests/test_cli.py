"""tests/test_cli.py — CLI integration tests."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Ensure migrations exist
from db import run_migrations
from db.albums import create_artist, create_album, list_albums
from db.sessions import open_session
from db.events import list_events


class TestCli(unittest.TestCase):
    """End-to-end CLI tests via subprocess."""

    @classmethod
    def setUpClass(cls):
        # Run the migrations once on the canonical db
        run_migrations()

    def test_status_cli(self):
        """The canonical Day 2 verification: 'status' CLI prints 4-line output."""
        result = subprocess.run(
            [sys.executable, "-m", "cli", "status"],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT)
        )
        self.assertEqual(result.returncode, 0)
        lines = result.stdout.strip().split("\n")
        self.assertEqual(len(lines), 4)
        # Per plan: active sessions / paused / done albums / quota remaining
        self.assertIn("active sessions:", lines[0])
        self.assertIn("paused:", lines[1])
        self.assertIn("done albums:", lines[2])
        self.assertIn("quota remaining:", lines[3])

    def test_list_albums_cli(self):
        """The canonical Day 2 verification: 'list albums' shows table."""
        result = subprocess.run(
            [sys.executable, "-m", "cli", "list", "albums"],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT)
        )
        self.assertEqual(result.returncode, 0)
        # Output either has data or "(no albums)"
        out = result.stdout.strip()
        self.assertTrue(
            "ID" in out or "no albums" in out,
            f"Unexpected output: {out!r}"
        )

    def test_list_sessions_cli(self):
        result = subprocess.run(
            [sys.executable, "-m", "cli", "list", "sessions"],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT)
        )
        self.assertEqual(result.returncode, 0)
        self.assertTrue(
            "ID" in result.stdout or "no sessions" in result.stdout,
            f"Unexpected output: {result.stdout!r}"
        )

    def test_serve_cli_prints_placeholder(self):
        """Day 3 will implement serve. Day 2 prints a placeholder message."""
        result = subprocess.run(
            [sys.executable, "-m", "cli", "serve"],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT)
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Day 3", result.stdout)

    def test_invoke_cli_prints_placeholder(self):
        """Day 6 will implement invoke. Day 2 prints a placeholder message."""
        result = subprocess.run(
            [sys.executable, "-m", "cli", "invoke", "music.generate"],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT)
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Day 6", result.stdout)

    def test_finalize_cli_prints_placeholder(self):
        result = subprocess.run(
            [sys.executable, "-m", "cli", "finalize", "half-light-hours"],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT)
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Day 11", result.stdout)

    def test_chat_cli(self):
        """Create a session, then 'chat' to add a message."""
        from db.sessions import open_session
        from db.albums import list_albums
        albums = list_albums()
        if not albums:
            # No album in canonical db yet — create one
            from db.albums import create_artist, create_album
            create_artist("chat-test", "Chat Test")
            create_album("chat-test", "Chat Test", "chat-test")
            target = "chat-test"
        else:
            target = albums[0]["id"]
        # Complete any existing active sessions first (max-3 guard)
        from db.sessions import list_sessions, complete_session
        existing = list_sessions(status="active", album_id=target, db_path=None)
        for sess in existing[:2]:
            complete_session(sess["id"])
        s = open_session(target)
        result = subprocess.run(
            [sys.executable, "-m", "cli", "chat",
             f"--session={s['id']}", "--message=hello"],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT)
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("event_id:", result.stdout)


if __name__ == "__main__":
    unittest.main()
