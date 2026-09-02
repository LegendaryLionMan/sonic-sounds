"""tests/test_cli.py — CLI integration tests.

Each test uses a fresh tempdb via the ALBUM_STUDIO_DB_PATH env var so the
live .meta/album-studio.db is never touched. The setUpClass creates one
tempdir for the whole class, runs migrations on it, and tears it down.

In-process DB setup helpers (create_artist/create_album/open_session) need
to be redirected to the tempdb as well — we do that by setting the
ALBUM_STUDIO_DB_PATH for the current process BEFORE importing the db
modules. Since the modules cache DEFAULT_DB_PATH at import time, the
setUpClass must run before any db.* import takes effect, which is why
this test imports db lazily inside class methods.
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# Note: we do NOT import db.* at module top, because DEFAULT_DB_PATH is
# resolved at import time and would capture the live .meta/album-studio.db.
# All db imports happen lazily inside setUpClass so the env var is set first.


class TestCli(unittest.TestCase):
    """End-to-end CLI tests via subprocess.

    Runs against a per-class tempdb so the live .meta/album-studio.db is
    never mutated by the test suite.
    """

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(PROJECT_ROOT))

        # Create a tempdir + tempdb for this class
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="album-studio-test-cli-"))
        cls.tempdb = cls.tmpdir / "test.db"

        # Set env BEFORE importing db modules so DEFAULT_DB_PATH picks up
        # the tempdb at import time.
        os.environ["ALBUM_STUDIO_DB_PATH"] = str(cls.tempdb)

        # Drop any cached db.* + build.* modules so they re-resolve DEFAULT_DB_PATH
        # with our env var. After this block, importing db.* will read
        # ALBUM_STUDIO_DB_PATH from the environment.
        for mod_name in list(sys.modules):
            if (mod_name == "db" or mod_name.startswith("db.")
                    or mod_name.startswith("build.")):
                del sys.modules[mod_name]

        from db import run_migrations
        from db.albums import create_artist, create_album, list_albums
        from db.sessions import (
            open_session, list_sessions, complete_session,
        )
        from db.events import list_events

        cls._db_modules = {
            "run_migrations": run_migrations,
            "create_artist": create_artist,
            "create_album": create_album,
            "list_albums": list_albums,
            "open_session": open_session,
            "list_sessions": list_sessions,
            "complete_session": complete_session,
            "list_events": list_events,
        }

        # Apply migrations to the tempdb explicitly
        run_migrations(db_path=cls.tempdb)

    @classmethod
    def tearDownClass(cls):
        # 1. Close any open connections to our tempdb before we delete
        #    the file. Drop db.* modules first so close_all() picks up the
        #    right cached conn (the test's tempdb, not the live one).
        os.environ["ALBUM_STUDIO_DB_PATH"] = str(cls.tempdb)
        for mod_name in list(sys.modules):
            if mod_name == "db" or mod_name.startswith("db."):
                del sys.modules[mod_name]
        try:
            from db.connection import close_all
            close_all()
        except Exception:
            pass  # best-effort cleanup
        # 2. Drop the cached db modules so the next test class re-resolves
        #    DEFAULT_DB_PATH fresh.
        for mod_name in list(sys.modules):
            if mod_name == "db" or mod_name.startswith("db."):
                del sys.modules[mod_name]
        # 3. Clean up the tempdir
        import shutil
        shutil.rmtree(cls.tmpdir, ignore_errors=True)
        # 4. Unset the env var so other test classes don't inherit it
        os.environ.pop("ALBUM_STUDIO_DB_PATH", None)

    def _subprocess_env(self) -> dict:
        """Build env for subprocess that points CLI at our tempdb."""
        env = os.environ.copy()
        env["ALBUM_STUDIO_DB_PATH"] = str(self.tempdb)
        return env

    def test_status_cli(self):
        """The canonical Day 2 verification: 'status' CLI prints 4-line output."""
        result = subprocess.run(
            [sys.executable, "-m", "cli", "status"],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT),
            env=self._subprocess_env(),
        )
        self.assertEqual(result.returncode, 0)
        lines = result.stdout.strip().split("\n")
        self.assertEqual(len(lines), 4)
        self.assertIn("active sessions:", lines[0])
        self.assertIn("paused:", lines[1])
        self.assertIn("done albums:", lines[2])
        self.assertIn("quota remaining:", lines[3])

    def test_list_albums_cli(self):
        """The canonical Day 2 verification: 'list albums' shows table."""
        result = subprocess.run(
            [sys.executable, "-m", "cli", "list", "albums"],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT),
            env=self._subprocess_env(),
        )
        self.assertEqual(result.returncode, 0)
        out = result.stdout.strip()
        self.assertTrue(
            "ID" in out or "no albums" in out,
            f"Unexpected output: {out!r}"
        )

    def test_list_sessions_cli(self):
        result = subprocess.run(
            [sys.executable, "-m", "cli", "list", "sessions"],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT),
            env=self._subprocess_env(),
        )
        self.assertEqual(result.returncode, 0)
        self.assertTrue(
            "ID" in result.stdout or "no sessions" in result.stdout,
            f"Unexpected output: {result.stdout!r}"
        )

    def test_serve_cli_prints_placeholder(self):
        """`python -m cli serve` should now delegate to the real daemon."""
        from cli import cmd_serve
        import inspect
        src = inspect.getsource(cmd_serve)
        self.assertIn("build.serve", src,
                      "cli.cmd_serve should delegate to build.serve.main")

    def test_invoke_cli_prints_placeholder(self):
        """Day 6 will implement invoke. Day 2 prints a placeholder message."""
        result = subprocess.run(
            [sys.executable, "-m", "cli", "invoke", "music.generate"],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT),
            env=self._subprocess_env(),
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Day 6", result.stdout)

    def test_finalize_cli_prints_placeholder(self):
        result = subprocess.run(
            [sys.executable, "-m", "cli", "finalize", "half-light-hours"],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT),
            env=self._subprocess_env(),
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Day 11", result.stdout)

    def test_chat_cli(self):
        """Create a session, then 'chat' to add a message.

        Uses tempdb (via ALBUM_STUDIO_DB_PATH in the subprocess env) and
        a unique artist/album id so the test doesn't collide with state
        left by other test classes.
        """
        env = self._subprocess_env()
        # Bootstrap artist + album in-process (faster than subprocess).
        # The db.* modules are already cached at the tempdb path because
        # setUpClass set ALBUM_STUDIO_DB_PATH and dropped the cached modules
        # before importing them.
        unique = f"chat-test-{os.getpid()}"
        self._db_modules["create_artist"](unique, "Chat Test")
        self._db_modules["create_album"](unique, "Chat Test", unique)

        # Open a session via in-process call (uses the same DEFAULT_DB_PATH
        # resolution the subprocess would use).
        s = self._db_modules["open_session"](unique)

        # Send a chat message via subprocess to exercise the actual CLI.
        result = subprocess.run(
            [sys.executable, "-m", "cli", "chat",
             f"--session={s['id']}", "--message=hello"],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT), env=env,
        )
        self.assertEqual(result.returncode, 0,
                         f"chat failed: {result.stderr!r}")
        self.assertIn("event_id:", result.stdout)


if __name__ == "__main__":
    unittest.main()