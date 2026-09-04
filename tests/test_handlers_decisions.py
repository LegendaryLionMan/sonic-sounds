"""tests/test_handlers_decisions.py — HTTP integration tests for /api/decisions/*.

Pattern (from tests/test_handlers_sessions.py):
- IsolatedAsyncioTestCase + Quart test_client
- Fresh tempdb per class via SONIC_STUDIO_DB_PATH
- Seeds artist + album + session at class setup; per-test decision IDs

Endpoints exercised:
  GET    /api/decisions                       — list (filters: ?album=, ?tier=, ?code=)
  POST   /api/decisions                       — append (201/400)
  GET    /api/decisions/<id>                  — get one (200/404)
  PATCH  /api/decisions/<id>                  — update (200/404/400)
  DELETE /api/decisions/<id>                  — hard delete (204/404)
  GET    /api/sessions/<id>/decisions         — session-scoped
  GET    /api/albums/<id>/decisions           — album-scoped
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _isolate_tempdb():
    """Create a tempdir + tempdb, point env at it, reload db.* + build.* modules."""
    tmpdir = Path(tempfile.mkdtemp(prefix="sonic-studio-test-decisions-"))
    tempdb = tmpdir / "test.db"
    os.environ["SONIC_STUDIO_DB_PATH"] = str(tempdb)
    for mod_name in list(sys.modules):
        if (mod_name == "db" or mod_name.startswith("db.")
                or mod_name.startswith("build.")):
            del sys.modules[mod_name]
    return tmpdir, tempdb


def _drop_isolation():
    """Mirror of _isolate_tempdb teardown."""
    from db.connection import close_all
    try:
        close_all()
    except Exception:
        pass
    for mod_name in list(sys.modules):
        if mod_name == "db" or mod_name.startswith("db."):
            del sys.modules[mod_name]
    os.environ.pop("SONIC_STUDIO_DB_PATH", None)


class TestDecisionsHandlers(unittest.IsolatedAsyncioTestCase):
    """Integration tests for /api/decisions/* and the session/album subroutes."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir, cls.tempdb = _isolate_tempdb()
        from db import migrations, albums as db_albums, sessions as db_sessions
        migrations.bootstrap_initial_migration(cls.tempdb)
        migrations.run_migrations(cls.tempdb)
        db_albums.create_artist("a1", "Artist", db_path=cls.tempdb)
        db_albums.create_album("al1", "Album One", "a1", db_path=cls.tempdb)
        db_albums.create_album("al2", "Album Two", "a1", db_path=cls.tempdb)
        sess = db_sessions.open_session("al1", db_path=cls.tempdb)
        cls.session_id = sess["id"]

    @classmethod
    def tearDownClass(cls):
        _drop_isolation()
        import shutil
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    async def asyncSetUp(self):
        from build.serve import create_app
        self.app = create_app()
        self.client = self.app.test_client()
        # Wipe decisions table between tests so filters and counts are
        # deterministic.
        import asyncio as _asyncio
        from db import connection as db_conn
        def _wipe():
            conn = db_conn.open_db()
            try:
                conn.execute("DELETE FROM decisions")
                conn.commit()
            finally:
                db_conn.close_db()
        await _asyncio.to_thread(_wipe)

    # ---- POST /api/decisions ----

    async def test_create_decision_201(self):
        resp = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory",
            "question": "What is the album title?",
            "answer": "Half-Light Hours",
            "album_id": "al1",
            "session_id": self.session_id,
        })
        self.assertEqual(resp.status_code, 201)
        body = await resp.get_json()
        self.assertEqual(body["code"], "M01")
        self.assertEqual(body["tier"], "mandatory")
        self.assertEqual(body["answer"], "Half-Light Hours")
        self.assertEqual(body["album_id"], "al1")
        self.assertEqual(body["session_id"], self.session_id)
        self.assertIn("id", body)

    async def test_create_decision_minimal_payload(self):
        """Only code + tier are required; everything else optional."""
        resp = await self.client.post("/api/decisions", json={
            "code": "Q01", "tier": "recommended",
        })
        self.assertEqual(resp.status_code, 201)
        body = await resp.get_json()
        self.assertEqual(body["code"], "Q01")
        self.assertEqual(body["tier"], "recommended")
        self.assertIsNone(body.get("answer"))

    async def test_create_decision_400_missing_code(self):
        resp = await self.client.post("/api/decisions", json={
            "tier": "mandatory",
        })
        self.assertEqual(resp.status_code, 400)
        body = await resp.get_json()
        self.assertIn("code", body["error"])

    async def test_create_decision_400_missing_tier(self):
        resp = await self.client.post("/api/decisions", json={
            "code": "M01",
        })
        self.assertEqual(resp.status_code, 400)
        body = await resp.get_json()
        self.assertIn("tier", body["error"])

    async def test_create_decision_400_invalid_tier(self):
        resp = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "ultra-mandatory",
        })
        self.assertEqual(resp.status_code, 400)
        body = await resp.get_json()
        self.assertIn("tier", body["error"])

    # ---- GET /api/decisions ----

    async def test_list_decisions_empty(self):
        resp = await self.client.get("/api/decisions")
        self.assertEqual(resp.status_code, 200)
        rows = await resp.get_json()
        self.assertEqual(rows, [])

    async def test_list_decisions_filter_by_album(self):
        """?album= returns only that album's decisions."""
        await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory", "album_id": "al1",
        })
        await self.client.post("/api/decisions", json={
            "code": "M02", "tier": "mandatory", "album_id": "al2",
        })
        resp = await self.client.get("/api/decisions?album=al1")
        self.assertEqual(resp.status_code, 200)
        rows = await resp.get_json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["code"], "M01")

    async def test_list_decisions_filter_by_tier(self):
        await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory",
        })
        await self.client.post("/api/decisions", json={
            "code": "R01", "tier": "recommended",
        })
        await self.client.post("/api/decisions", json={
            "code": "X01", "tier": "extra",
        })
        resp = await self.client.get("/api/decisions?tier=mandatory")
        rows = await resp.get_json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["code"], "M01")

    # ---- GET /api/decisions/<id> ----

    async def test_get_decision_200(self):
        create = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory", "answer": "lock",
        })
        did = (await create.get_json())["id"]
        resp = await self.client.get(f"/api/decisions/{did}")
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertEqual(body["id"], did)
        self.assertEqual(body["answer"], "lock")

    async def test_get_decision_404(self):
        resp = await self.client.get("/api/decisions/999999")
        self.assertEqual(resp.status_code, 404)

    # ---- PATCH /api/decisions/<id> ----

    async def test_patch_decision_200(self):
        """Update answer; locked_at should be bumped."""
        create = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory", "answer": "old",
        })
        did = (await create.get_json())["id"]
        old_locked = (await create.get_json())["locked_at"]

        resp = await self.client.patch(f"/api/decisions/{did}", json={
            "answer": "new", "rationale": "because",
        })
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertEqual(body["answer"], "new")
        self.assertEqual(body["rationale"], "because")
        # locked_at was bumped
        self.assertNotEqual(body["locked_at"], old_locked)

    async def test_patch_decision_400_no_fields(self):
        create = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory",
        })
        did = (await create.get_json())["id"]
        resp = await self.client.patch(f"/api/decisions/{did}", json={
            "ignored": "field",
        })
        self.assertEqual(resp.status_code, 400)

    async def test_patch_decision_404(self):
        resp = await self.client.patch("/api/decisions/999999", json={
            "answer": "x",
        })
        self.assertEqual(resp.status_code, 404)

    # ---- DELETE /api/decisions/<id> ----

    async def test_delete_decision_204(self):
        create = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory",
        })
        did = (await create.get_json())["id"]
        resp = await self.client.delete(f"/api/decisions/{did}")
        self.assertEqual(resp.status_code, 204)
        # Subsequent GET is 404
        get = await self.client.get(f"/api/decisions/{did}")
        self.assertEqual(get.status_code, 404)

    async def test_delete_decision_404(self):
        resp = await self.client.delete("/api/decisions/999999")
        self.assertEqual(resp.status_code, 404)

    # ---- Session / album scoped convenience ----

    async def test_list_session_decisions(self):
        await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory",
            "session_id": self.session_id,
        })
        await self.client.post("/api/decisions", json={
            "code": "M02", "tier": "mandatory",
            "session_id": self.session_id,
        })
        await self.client.post("/api/decisions", json={
            "code": "M03", "tier": "mandatory",
            "session_id": "other-session-id",  # not the one we filter on
        })
        resp = await self.client.get(f"/api/sessions/{self.session_id}/decisions")
        self.assertEqual(resp.status_code, 200)
        rows = await resp.get_json()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["session_id"] == self.session_id for r in rows))

    async def test_list_album_decisions(self):
        await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory", "album_id": "al1",
        })
        await self.client.post("/api/decisions", json={
            "code": "M02", "tier": "mandatory", "album_id": "al1",
        })
        await self.client.post("/api/decisions", json={
            "code": "M03", "tier": "mandatory", "album_id": "al2",
        })
        resp = await self.client.get("/api/albums/al1/decisions")
        self.assertEqual(resp.status_code, 200)
        rows = await resp.get_json()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["album_id"] == "al1" for r in rows))
