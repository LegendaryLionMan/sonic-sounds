"""tests/test_handlers_sessions.py — HTTP integration tests for /api/sessions/*.

Pattern (from tests/test_serve.py + test_handlers_albums.py):
- IsolatedAsyncioTestCase + Quart test_client
- Fresh tempdb per class via SONIC_STUDIO_DB_PATH
- Seeds artists + albums at class setup; per-test session IDs

The state machine is the centerpiece: pause/resume/complete have
nuanced transitions and the max-3 guard under concurrency is the
biggest non-trivial test in this file.
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


def _isolate_tempdb():
    """Create a tempdir + tempdb, point env at it, reload db.* + build.* modules.

    Same rationale as in test_handlers_albums.py:_isolate_tempdb:
    cached top-level `from db.queries import global_status` in
    build/serve.py would otherwise keep references to OLD db.connection
    modules whose connections are never closed by the NEW module's
    close_all(), causing "database is locked" failures in the new
    test class's _reseed_albums.
    """
    tmpdir = Path(tempfile.mkdtemp(prefix="sonic-studio-test-sessions-"))
    tempdb = tmpdir / "test.db"
    os.environ["SONIC_STUDIO_DB_PATH"] = str(tempdb)
    for mod_name in list(sys.modules):
        if (mod_name == "db" or mod_name.startswith("db.")
                or mod_name.startswith("build.")):
            del sys.modules[mod_name]
    return tmpdir, tempdb


def _drop_isolation():
    """Mirror of _isolate_tempdb teardown.

    Critical: connections must be CLOSED (not just orphaned) before the
    tempdb file is deleted. The per-thread + cross-thread registry in
    db.connection holds open sqlite3.Connection objects; if those outlive
    the tempdb file, the next test class's fresh open_db() will hit
    "database is locked" because the old WAL file's writers are still
    alive in cached threads.

    Sequence:
      1. Close all connections (must import BEFORE deleting db modules).
      2. Drop the cached db.* modules so the next test class re-resolves
         DEFAULT_DB_PATH fresh.

    close_all() also clears the per-thread cache for every known thread
    (after the 2026-09-02 fix that replaced threading.local() with a
    module-level dict keyed on thread ident).
    """
    # 1. Close while the import path is still intact.
    from db.connection import close_all
    try:
        close_all()
    except Exception:
        pass

    # 2. Drop the cached db.* modules.
    for mod_name in list(sys.modules):
        if mod_name == "db" or mod_name.startswith("db."):
            del sys.modules[mod_name]
    os.environ.pop("SONIC_STUDIO_DB_PATH", None)


def _reset_sessions_table(db_sessions, db_conn):
    """Wipe the album_sessions table before each test.

    Sessions are stateful (max-3 active guard, status transitions), so
    leftover sessions from earlier tests poison later ones. This is
    called from asyncSetUp via asyncio.to_thread so it runs on a worker
    thread (matching the threading model of open_db).
    """
    conn = db_conn.open_db()
    try:
        # album_sessions.album_id has ON DELETE CASCADE so a plain
        # DELETE FROM album_sessions works without affecting albums.
        conn.execute("DELETE FROM album_sessions")
        conn.commit()
    finally:
        db_conn.close_db()


def _reseed_albums(db_albums, db_conn, tempdb):
    """Restore al1..al4 before each test.

    Wipes album_sessions + albums then recreates al1..al4. The artist
    a1 must already exist (seeded in setUpClass).
    """
    db_conn.close_all()
    conn = db_conn.open_db()
    try:
        conn.execute("DELETE FROM album_sessions")
        conn.execute("DELETE FROM albums")
        conn.commit()
    finally:
        db_conn.close_db()
    titles = {1: "Album One", 2: "Album Two", 3: "Album Three", 4: "Album Four"}
    for i in range(1, 5):
        db_albums.create_album(f"al{i}", titles[i], "a1", db_path=tempdb)


class TestSessionsHandlers(unittest.IsolatedAsyncioTestCase):
    """Integration tests for /api/sessions/*."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir, cls.tempdb = _isolate_tempdb()
        from db import migrations, albums as db_albums
        migrations.bootstrap_initial_migration(cls.tempdb)
        migrations.run_migrations(cls.tempdb)
        # 4 albums so the max-3 guard tests have room
        db_albums.create_artist("a1", "Artist", db_path=cls.tempdb)
        for i in range(1, 5):
            db_albums.create_album(f"al{i}", f"Album {i}", "a1", db_path=cls.tempdb)

    @classmethod
    def tearDownClass(cls):
        _drop_isolation()
        import shutil
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    async def asyncSetUp(self):
        from build.serve import create_app
        self.app = create_app()
        self.client = self.app.test_client()
        # Per-test isolation: restore al1..al4 + clear sessions so the
        # state machine (max-3 active guard, transitions) and the album
        # assertions both have a known starting state.
        import asyncio as _asyncio
        from db import connection as db_conn, albums as db_albums
        await _asyncio.to_thread(_reseed_albums, db_albums, db_conn, self.__class__.tempdb)

    # ---- POST /api/sessions ----

    async def test_open_session_201(self):
        resp = await self.client.post("/api/sessions", json={"album_id": "al1"})
        self.assertEqual(resp.status_code, 201)
        body = await resp.get_json()
        self.assertEqual(body["album_id"], "al1")
        self.assertEqual(body["status"], "active")
        self.assertIn("id", body)
        # Save for follow-up tests
        self.__class__.session_id = body["id"]

    async def test_open_session_400_missing_album_id(self):
        resp = await self.client.post("/api/sessions", json={})
        self.assertEqual(resp.status_code, 400)

    async def test_open_session_400_album_not_found(self):
        resp = await self.client.post("/api/sessions", json={"album_id": "ghost"})
        self.assertEqual(resp.status_code, 400)
        body = await resp.get_json()
        self.assertIn("not found", body["error"])

    async def test_open_session_409_max_active(self):
        """Sequential opens should yield 3×201 and 1×409 (max-3 guard).

        Note: we run sequentially (not asyncio.gather) because the
        event loop is single-threaded — gather wouldn't actually race
        the requests, and the BEGIN IMMEDIATE serialization in
        db/sessions.py makes sequential opens the more deterministic
        test of the max-3 logic. The race-safety property is already
        pinned by TestOpenSessionRace in test_regressions.py.
        """
        statuses = []
        bodies = []
        for album in ("al1", "al2", "al3", "al4"):
            r = await self.client.post("/api/sessions", json={"album_id": album})
            statuses.append(r.status_code)
            bodies.append(await r.get_json())
        self.assertEqual(statuses.count(201), 3,
                         f"Expected 3 successes, got {statuses} bodies={bodies}")
        self.assertEqual(statuses.count(409), 1,
                         f"Expected 1 conflict, got {statuses} bodies={bodies}")

    # ---- GET /api/sessions/<id> ----

    async def test_get_session_200(self):
        # Use a fresh session for isolation
        resp = await self.client.post("/api/sessions", json={"album_id": "al1"})
        self.assertEqual(resp.status_code, 201)
        sid = (await resp.get_json())["id"]

        r2 = await self.client.get(f"/api/sessions/{sid}")
        self.assertEqual(r2.status_code, 200)
        body = await r2.get_json()
        self.assertEqual(body["id"], sid)

    async def test_get_session_404(self):
        r = await self.client.get("/api/sessions/nope")
        self.assertEqual(r.status_code, 404)

    # ---- State transitions ----

    async def test_pause_then_resume_session(self):
        resp = await self.client.post("/api/sessions", json={"album_id": "al2"})
        sid = (await resp.get_json())["id"]

        r2 = await self.client.post(f"/api/sessions/{sid}/pause")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual((await r2.get_json())["status"], "paused")

        r3 = await self.client.post(f"/api/sessions/{sid}/resume")
        self.assertEqual(r3.status_code, 200)
        self.assertEqual((await r3.get_json())["status"], "active")

    async def test_resume_409_when_already_active(self):
        resp = await self.client.post("/api/sessions", json={"album_id": "al3"})
        sid = (await resp.get_json())["id"]

        r2 = await self.client.post(f"/api/sessions/{sid}/resume")
        self.assertEqual(r2.status_code, 409)
        body = await r2.get_json()
        self.assertIn("active", body["error"])

    async def test_pause_409_when_already_paused(self):
        resp = await self.client.post("/api/sessions", json={"album_id": "al4"})
        sid = (await resp.get_json())["id"]
        await self.client.post(f"/api/sessions/{sid}/pause")
        # Pause again — should 409
        r2 = await self.client.post(f"/api/sessions/{sid}/pause")
        self.assertEqual(r2.status_code, 409)

    async def test_complete_session_terminal(self):
        resp = await self.client.post("/api/sessions", json={"album_id": "al1"})
        sid = (await resp.get_json())["id"]

        r2 = await self.client.post(f"/api/sessions/{sid}/complete")
        self.assertEqual(r2.status_code, 200)
        body = await r2.get_json()
        self.assertEqual(body["status"], "done")
        self.assertIsNotNone(body["closed_at"])

        # Subsequent pause should 409 (done is terminal)
        r3 = await self.client.post(f"/api/sessions/{sid}/pause")
        self.assertEqual(r3.status_code, 409)

    async def test_transition_404_when_session_missing(self):
        for action in ("pause", "resume", "complete"):
            r = await self.client.post(f"/api/sessions/nope/{action}")
            self.assertEqual(r.status_code, 404, f"{action}: expected 404, got {r.status_code}")

    # ---- Read-only helpers ----

    async def test_idle_hours_200(self):
        resp = await self.client.post("/api/sessions", json={"album_id": "al2"})
        sid = (await resp.get_json())["id"]

        r2 = await self.client.get(f"/api/sessions/{sid}/idle_hours")
        self.assertEqual(r2.status_code, 200)
        body = await r2.get_json()
        self.assertIn("idle_hours", body)
        self.assertGreaterEqual(body["idle_hours"], 0)

    async def test_idle_hours_404(self):
        r = await self.client.get("/api/sessions/nope/idle_hours")
        self.assertEqual(r.status_code, 404)

    async def test_touch_session_200(self):
        resp = await self.client.post("/api/sessions", json={"album_id": "al3"})
        sid = (await resp.get_json())["id"]

        r2 = await self.client.post(f"/api/sessions/{sid}/touch")
        self.assertEqual(r2.status_code, 200)
        body = await r2.get_json()
        self.assertTrue(body["touched"])

    async def test_touch_404_when_session_missing(self):
        r = await self.client.post("/api/sessions/nope/touch")
        self.assertEqual(r.status_code, 404)


if __name__ == "__main__":
    unittest.main()
