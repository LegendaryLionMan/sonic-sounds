"""tests/test_handlers_albums.py — HTTP integration tests for /api/albums/*.

Pattern (from tests/test_serve.py):
- IsolatedAsyncioTestCase + Quart test_client
- Fresh tempdb per class via ALBUM_STUDIO_DB_PATH
- Each test seeds its own artist + album so the JSON shape is predictable
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

    Mirrors test_serve.py:TestServe.setUpClass but extended to also
    drop the build.* modules (handlers_albums, handlers_sessions, serve).
    Without that, a cached `from db.queries import global_status` at
    build/serve.py's top level would still reference the OLD
    db.connection.open_db, whose `default_db_path()` would read the NEW
    env but its connection would be registered in the OLD
    `_thread_registry` — never closed by the NEW module's close_all().
    """
    tmpdir = Path(tempfile.mkdtemp(prefix="album-studio-test-albums-"))
    tempdb = tmpdir / "test.db"
    os.environ["ALBUM_STUDIO_DB_PATH"] = str(tempdb)
    for mod_name in list(sys.modules):
        if (mod_name == "db" or mod_name.startswith("db.")
                or mod_name.startswith("build.")):
            del sys.modules[mod_name]
    return tmpdir, tempdb


def _drop_isolation():
    """Mirror of _isolate_tempdb teardown.

    Critical: connections must be CLOSED before the tempdb file is deleted,
    or the next test class's open_db() hits "database is locked" because
    the orphaned WAL writer connections are still alive in cached threads.

    close_all() now also clears every thread's per-thread cache, so we
    just need to drop the cached db.* modules.
    """
    from db.connection import close_all
    try:
        close_all()
    except Exception:
        pass

    for mod_name in list(sys.modules):
        if mod_name == "db" or mod_name.startswith("db."):
            del sys.modules[mod_name]
    os.environ.pop("ALBUM_STUDIO_DB_PATH", None)


def _reseed_albums(db_albums, db_conn, tempdb):
    """Restore al1..al4 before each test.

    Some tests archive al3 or create al2/al3/al4 dynamically. Before
    each test we delete the transient rows and recreate the canonical
    al1..al4 set so the test's assertions on /api/albums/<id> always work.

    Also wipes the sessions table because archived albums would have
    blocked if their sessions survived.

    The artist `a1` must already exist (seeded in setUpClass); we don't
    re-create it here because doing so would FK-cascade-delete the albums
    we're about to recreate.
    """
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


class TestAlbumsHandlers(unittest.IsolatedAsyncioTestCase):
    """Integration tests for /api/albums/*."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir, cls.tempdb = _isolate_tempdb()
        # Seed an artist + album so tests have something to query
        from db import migrations, albums as db_albums
        migrations.bootstrap_initial_migration(cls.tempdb)
        migrations.run_migrations(cls.tempdb)
        db_albums.create_artist("a1", "Artist One", db_path=cls.tempdb)
        db_albums.create_album("al1", "Album One", "a1",
                               release_date="2026-09-21", runtime_min=40,
                               db_path=cls.tempdb)

    @classmethod
    def tearDownClass(cls):
        _drop_isolation()
        import shutil
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    async def asyncSetUp(self):
        from build.serve import create_app
        self.app = create_app()
        self.client = self.app.test_client()
        # Per-test isolation: clear transient tables so tests don't bleed.
        # We keep artists (seeded once in setUpClass) and albums al1..al4
        # (also seeded once). We wipe any extras (al2 in test_archive_album_200
        # etc.) by recreating al1..al4 from a snapshot before each test.
        import asyncio as _asyncio
        from db import connection as db_conn, albums as db_albums
        await _asyncio.to_thread(_reseed_albums, db_albums, db_conn, self.__class__.tempdb)

    # ---- GET /api/albums ----

    async def test_list_albums_returns_seed(self):
        resp = await self.client.get("/api/albums")
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertIsInstance(body, list)
        ids = [a["id"] for a in body]
        self.assertIn("al1", ids)

    async def test_list_albums_filter_by_status(self):
        resp = await self.client.get("/api/albums?status=active")
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertTrue(all(a["status"] == "active" for a in body))

    # ---- POST /api/albums ----

    async def test_create_album_201(self):
        # Use al5 — al1..al4 are reseeded by asyncSetUp and always present.
        resp = await self.client.post("/api/albums", json={
            "id": "al5", "title": "Album Five", "primary_artist_id": "a1",
            "runtime_min": 35,
        })
        self.assertEqual(resp.status_code, 201)
        body = await resp.get_json()
        self.assertEqual(body["id"], "al5")
        self.assertEqual(body["title"], "Album Five")
        self.assertEqual(body["status"], "active")

    async def test_create_album_400_missing_field(self):
        resp = await self.client.post("/api/albums", json={
            "title": "No ID",
        })
        self.assertEqual(resp.status_code, 400)
        body = await resp.get_json()
        self.assertIn("error", body)
        self.assertIn("id", body["error"])

    async def test_create_album_409_duplicate(self):
        # al1 is reseeded every test, so posting it again is a guaranteed dup
        resp = await self.client.post("/api/albums", json={
            "id": "al1", "title": "Duplicate", "primary_artist_id": "a1",
        })
        self.assertEqual(resp.status_code, 409)

    # ---- GET /api/albums/<id> ----

    async def test_get_album_200(self):
        resp = await self.client.get("/api/albums/al1")
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertEqual(body["id"], "al1")
        self.assertEqual(body["title"], "Album One")

    async def test_get_album_404(self):
        resp = await self.client.get("/api/albums/nope")
        self.assertEqual(resp.status_code, 404)

    # ---- PATCH /api/albums/<id> ----

    async def test_patch_album_200(self):
        resp = await self.client.patch("/api/albums/al1", json={
            "title": "Album One (Revised)",
            "runtime_min": 42,
        })
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertEqual(body["title"], "Album One (Revised)")
        self.assertEqual(body["runtime_min"], 42)

    async def test_patch_album_404(self):
        resp = await self.client.patch("/api/albums/nope", json={"title": "x"})
        self.assertEqual(resp.status_code, 404)

    async def test_patch_album_strips_unknown_fields(self):
        """Unknown fields (e.g. 'created_at') should be silently ignored,
        not persisted."""
        resp = await self.client.patch("/api/albums/al1", json={
            "title": "OK",
            "created_at": "1970-01-01",  # should be stripped
        })
        self.assertEqual(resp.status_code, 200)
        # Reload and verify created_at wasn't clobbered
        body = await resp.get_json()
        self.assertNotEqual(body["created_at"], "1970-01-01")

    # ---- POST /api/albums/<id>/archive ----

    async def test_archive_album_200(self):
        # Archive al4 — it's the only album id never touched by other tests.
        resp = await self.client.post("/api/albums/al4/archive")
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertEqual(body["status"], "archived")

    async def test_archive_album_404(self):
        resp = await self.client.post("/api/albums/nope/archive")
        self.assertEqual(resp.status_code, 404)

    # ---- GET /api/albums/<id>/tracks ----

    async def test_list_album_tracks_empty(self):
        resp = await self.client.get("/api/albums/al1/tracks")
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertEqual(body, [])

    # ---- GET /api/albums/<id>/assets ----

    async def test_list_album_assets_empty(self):
        resp = await self.client.get("/api/albums/al1/assets")
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertEqual(body, [])

    # ---- GET /api/albums/<id>/sessions ----

    async def test_list_album_sessions_empty(self):
        resp = await self.client.get("/api/albums/al1/sessions")
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertEqual(body, [])


if __name__ == "__main__":
    unittest.main()
