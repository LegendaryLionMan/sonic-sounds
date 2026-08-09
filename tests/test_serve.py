"""tests/test_serve.py — integration tests via Quart's test_client (Day 3).

Standard Quart testing pattern:
  - Use `unittest.IsolatedAsyncioTestCase` for async test methods
  - QuartClient.get() is async; use `await self.client.get(...)`
  - Quart 0.21: resp.data is async — use `resp.get_data()` (bytes)
  - For JSON: use `resp.get_json()` directly
"""
import json
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
    """Integration tests using Quart's async test_client."""

    async def asyncSetUp(self):
        run_migrations()
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
