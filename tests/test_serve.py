"""tests/test_serve.py — integration tests via Quart's test_client (Day 3).

Standard Quart testing pattern:
  - Use `unittest.IsolatedAsyncioTestCase` for async test methods
  - QuartClient.get() is async; use `await self.client.get(...)`
  - Quart 0.21: resp.data is async — use `resp.get_data()` (bytes)
  - For JSON: use `resp.get_json()` directly

Test isolation: each class run uses a fresh tempdb via ALBUM_STUDIO_DB_PATH
so the live .meta/album-studio.db is never mutated.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from build.serve import create_app
from db import run_migrations


class TestServe(unittest.IsolatedAsyncioTestCase):
    """Integration tests using Quart's async test_client.

    Each class run uses a fresh tempdb (set via ALBUM_STUDIO_DB_PATH)
    so the live .meta/album-studio.db is never mutated.
    """

    @classmethod
    def setUpClass(cls):
        # Create a tempdir + tempdb for this class
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="album-studio-test-serve-"))
        cls.tempdb = cls.tmpdir / "test.db"

        # Set env BEFORE importing db modules
        os.environ["ALBUM_STUDIO_DB_PATH"] = str(cls.tempdb)

        # Drop cached db.* + build.* modules so they re-resolve DEFAULT_DB_PATH
        # with our env var. The build.* modules must also be dropped because
        # they cache top-level `from db.queries import ...` references which
        # would otherwise pin the OLD db.connection.open_db function whose
        # registered connections would never be closed by our NEW
        # module's close_all() (see "tool-path commitment" in MEMORY.md).
        for mod_name in list(sys.modules):
            if (mod_name == "db" or mod_name.startswith("db.")
                    or mod_name.startswith("build.")):
                del sys.modules[mod_name]

        # Now (re-)import run_migrations so DEFAULT_DB_PATH is captured
        # at our tempdb, not the live one.
        global run_migrations
        from db import run_migrations as _rm
        run_migrations = _rm

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

    async def asyncSetUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    # === Health endpoint ===

    async def test_health_endpoint(self):
        resp = await self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertEqual(body["status"], "ok")
        self.assertIn("subsystems", body)
        self.assertIn("counts", body)
        self.assertIn("db", body["subsystems"])
        self.assertEqual(body["subsystems"]["db"], "ok")
        self.assertIn("timestamp", body)

    # === Static file endpoints ===

    async def test_site_static_index(self):
        resp = await self.client.get("/site/index.html")
        self.assertEqual(resp.status_code, 200)
        body = (await resp.get_data()).decode()
        self.assertIn("<!doctype html>", body.lower())

    async def test_site_static_path_traversal_blocked(self):
        resp = await self.client.get("/site/../../etc/passwd")
        self.assertIn(resp.status_code, (403, 404))

    async def test_site_static_not_found(self):
        resp = await self.client.get("/site/nonexistent.html")
        self.assertEqual(resp.status_code, 404)

    async def test_assets_static(self):
        """CSS is in site/css/ — test the /site/ route serves it correctly."""
        resp = await self.client.get("/site/css/components.css")
        self.assertEqual(resp.status_code, 200)
        body = (await resp.get_data()).decode()
        self.assertIn(":root", body)

    async def test_assets_path_traversal_blocked(self):
        resp = await self.client.get("/site/../db/schema.sql")
        self.assertIn(resp.status_code, (403, 404))

    # === List endpoints ===

    async def test_list_albums(self):
        resp = await self.client.get("/api/albums")
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertIsInstance(body, list)

    async def test_list_sessions(self):
        resp = await self.client.get("/api/sessions")
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertIsInstance(body, list)

    # === Audio endpoint ===

    async def test_audio_404_for_unknown_track(self):
        resp = await self.client.get("/api/audio/nonexistent")
        self.assertEqual(resp.status_code, 404)

    async def test_audio_endpoint_handles_repeated_requests(self):
        """Regression: the audio endpoint used to close its per-thread
        connection without removing it from the cache, so the second
        request from the same worker thread would crash with
        'Cannot operate on a closed database'. The fix uses close_db()
        which pops from the cache."""
        # Make multiple requests in sequence. If the cache poisoning
        # bug regresses, the second request raises ProgrammingError
        # which Quart surfaces as 500.
        statuses = []
        for i in range(3):
            resp = await self.client.get("/api/audio/nonexistent")
            statuses.append(resp.status_code)
        # All should be 404 (track not found), none should be 500
        self.assertEqual(statuses, [404, 404, 404],
                         f"Expected repeated 404s, got {statuses}")


class TestSingleton(unittest.TestCase):
    """SingletonLock tests (independent of HTTP)."""

    def test_singleton_lock_stale_pid_takeover(self):
        """A lock with a dead PID should be taken over."""
        from build.singleton import SingletonLock
        with tempfile.NamedTemporaryFile(suffix=".lock", delete=False) as f:
            lock_path = Path(f.name)
        try:
            lock_path.write_text("999999\n")
            lock = SingletonLock(lock_path)
            lock.acquire()  # should take over stale lock
            # After acquire, our PID should be in the file
            pid_in_file = int(lock_path.read_text().strip())
            import os
            self.assertEqual(pid_in_file, os.getpid())
            lock.release()
        finally:
            if lock_path.exists():
                lock_path.unlink()

    def test_singleton_lock_release_removes_file(self):
        from build.singleton import SingletonLock
        with tempfile.NamedTemporaryFile(suffix=".lock", delete=False) as f:
            lock_path = Path(f.name)
        try:
            lock = SingletonLock(lock_path)
            lock.acquire()
            self.assertTrue(lock_path.exists())
            lock.release()
            self.assertFalse(lock_path.exists())
        finally:
            if lock_path.exists():
                lock_path.unlink()

    def test_singleton_lock_same_process_reacquire(self):
        """Same-process re-acquire is a no-op (doesn't raise)."""
        from build.singleton import SingletonLock
        with tempfile.NamedTemporaryFile(suffix=".lock", delete=False) as f:
            lock_path = Path(f.name)
        try:
            lock1 = SingletonLock(lock_path)
            lock1.acquire()
            # Second acquire on same PID should be silent no-op
            lock2 = SingletonLock(lock_path)
            lock2.acquire()  # should NOT raise
            import os
            self.assertEqual(int(lock_path.read_text().strip()), os.getpid())
            lock1.release()
        finally:
            if lock_path.exists():
                lock_path.unlink()


if __name__ == "__main__":
    unittest.main()
