"""tests/test_handlers_events.py — HTTP integration tests for /api/events/*.

Pattern (from tests/test_handlers_sessions.py):
- IsolatedAsyncioTestCase + Quart test_client
- Fresh tempdb per class via SONIC_SOUNDS_DB_PATH
- Seeds artist + album + session at class setup; per-test event IDs

Endpoints exercised:
  GET    /api/events                       — list (requires ?session=)
  POST   /api/events                       — append (201/400)
  GET    /api/events/<id>                  — get one (200/404)
  GET    /api/sessions/<id>/events         — session-scoped list
  GET    /api/sessions/<id>/events/latest_id  — polling cursor
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

    Same rationale as test_handlers_sessions.py — cached top-level
    `from db.queries import global_status` in build/serve.py would
    otherwise keep references to OLD db.connection modules whose
    connections are never closed by the NEW module's close_all().
    """
    tmpdir = Path(tempfile.mkdtemp(prefix="sonic-sounds-test-events-"))
    tempdb = tmpdir / "test.db"
    os.environ["SONIC_SOUNDS_DB_PATH"] = str(tempdb)
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
    os.environ.pop("SONIC_SOUNDS_DB_PATH", None)


class TestEventsHandlers(unittest.IsolatedAsyncioTestCase):
    """Integration tests for /api/events/* and the session-scoped subroutes."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir, cls.tempdb = _isolate_tempdb()
        from db import migrations, albums as db_albums, sessions as db_sessions
        migrations.bootstrap_initial_migration(cls.tempdb)
        migrations.run_migrations(cls.tempdb)
        db_albums.create_artist("a1", "Artist", db_path=cls.tempdb)
        db_albums.create_album("al1", "Album One", "a1", db_path=cls.tempdb)
        # One pre-opened session that all tests reuse
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
        # Wipe events table between tests so the latest_id and list
        # endpoints are deterministic.
        import asyncio as _asyncio
        from db import connection as db_conn
        def _wipe():
            conn = db_conn.open_db()
            try:
                conn.execute("DELETE FROM events")
                conn.commit()
            finally:
                db_conn.close_db()
        await _asyncio.to_thread(_wipe)

    # ---- POST /api/events ----

    async def test_create_event_201(self):
        resp = await self.client.post("/api/events", json={
            "session_id": self.session_id,
            "role": "user",
            "kind": "chat",
            "content": "hello world",
        })
        self.assertEqual(resp.status_code, 201)
        body = await resp.get_json()
        self.assertEqual(body["session_id"], self.session_id)
        self.assertEqual(body["role"], "user")
        self.assertEqual(body["kind"], "chat")
        self.assertEqual(body["content"], "hello world")
        self.assertIn("id", body)
        self.assertIn("created_at", body)

    async def test_create_event_with_payload_and_album_id(self):
        """Payload dict + album_id round-trip as JSON-serialized columns."""
        resp = await self.client.post("/api/events", json={
            "session_id": self.session_id,
            "role": "assistant",
            "kind": "build",
            "content": "Starting lyrics layer",
            "album_id": "al1",
            "payload": {"layer": 3, "phase": "lyrics_finalize"},
        })
        self.assertEqual(resp.status_code, 201)
        body = await resp.get_json()
        self.assertEqual(body["album_id"], "al1")
        # payload comes back as a parsed dict (jsonify on the way out)
        self.assertIsInstance(body["payload"], dict)
        self.assertEqual(body["payload"]["layer"], 3)

    async def test_create_event_400_missing_session(self):
        resp = await self.client.post("/api/events", json={
            "role": "user", "kind": "chat", "content": "no session",
        })
        self.assertEqual(resp.status_code, 400)
        body = await resp.get_json()
        self.assertIn("session_id", body["error"])

    async def test_create_event_400_invalid_role(self):
        resp = await self.client.post("/api/events", json={
            "session_id": self.session_id,
            "role": "robot", "kind": "chat",
        })
        self.assertEqual(resp.status_code, 400)
        body = await resp.get_json()
        self.assertIn("role", body["error"].lower())

    async def test_create_event_400_invalid_kind(self):
        resp = await self.client.post("/api/events", json={
            "session_id": self.session_id,
            "role": "user", "kind": "spam",
        })
        self.assertEqual(resp.status_code, 400)

    async def test_create_event_400_unknown_session(self):
        """A session_id that doesn't exist must be rejected — we don't
        want dangling events with a fake FK."""
        resp = await self.client.post("/api/events", json={
            "session_id": "ghost-session-id",
            "role": "user", "kind": "chat", "content": "x",
        })
        self.assertEqual(resp.status_code, 400)
        body = await resp.get_json()
        self.assertIn("not found", body["error"])

    # ---- GET /api/events ----

    async def test_list_events_400_without_session_filter(self):
        """Without ?session=, we reject to prevent accidental full-table scans."""
        resp = await self.client.get("/api/events")
        self.assertEqual(resp.status_code, 400)

    async def test_list_events_200_with_session_filter(self):
        """Seed 2 events then list them via ?session=."""
        for i in range(2):
            await self.client.post("/api/events", json={
                "session_id": self.session_id,
                "role": "user", "kind": "chat",
                "content": f"msg {i}",
            })
        resp = await self.client.get(f"/api/events?session={self.session_id}")
        self.assertEqual(resp.status_code, 200)
        rows = await resp.get_json()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["content"], "msg 0")
        self.assertEqual(rows[1]["content"], "msg 1")

    async def test_list_events_kind_filter(self):
        """?kind= filters to events of that kind only."""
        await self.client.post("/api/events", json={
            "session_id": self.session_id, "role": "user", "kind": "chat",
            "content": "chat 1",
        })
        await self.client.post("/api/events", json={
            "session_id": self.session_id, "role": "assistant", "kind": "build",
            "content": "build 1",
        })
        await self.client.post("/api/events", json={
            "session_id": self.session_id, "role": "assistant", "kind": "build",
            "content": "build 2",
        })
        resp = await self.client.get(f"/api/events?session={self.session_id}&kind=build")
        self.assertEqual(resp.status_code, 200)
        rows = await resp.get_json()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["kind"] == "build" for r in rows))

    async def test_list_events_since_id_cursor(self):
        """?since_id=N returns events with id > N.

        This is the polling cursor. It must survive second-precision
        timestamp collisions (multiple events with the same created_at
        must still be ordered deterministically by id).
        """
        ids = []
        for i in range(3):
            r = await self.client.post("/api/events", json={
                "session_id": self.session_id, "role": "user", "kind": "chat",
                "content": f"msg {i}",
            })
            ids.append((await r.get_json())["id"])

        # since_id = first id → should return 2 (ids[1], ids[2])
        resp = await self.client.get(
            f"/api/events?session={self.session_id}&since_id={ids[0]}"
        )
        self.assertEqual(resp.status_code, 200)
        rows = await resp.get_json()
        self.assertEqual(len(rows), 2)
        self.assertEqual([r["id"] for r in rows], [ids[1], ids[2]])

        # since_id = last id → should return 0
        resp = await self.client.get(
            f"/api/events?session={self.session_id}&since_id={ids[-1]}"
        )
        rows = await resp.get_json()
        self.assertEqual(len(rows), 0)

    async def test_list_events_since_id_invalid(self):
        """?since_id=garbage → 400, not 500."""
        resp = await self.client.get(
            f"/api/events?session={self.session_id}&since_id=notanint"
        )
        self.assertEqual(resp.status_code, 400)
        body = await resp.get_json()
        self.assertIn("since_id", body["error"])

    # ---- GET /api/events/<id> ----

    async def test_get_event_200(self):
        create = await self.client.post("/api/events", json={
            "session_id": self.session_id,
            "role": "system", "kind": "log",
            "content": "session opened",
        })
        eid = (await create.get_json())["id"]
        resp = await self.client.get(f"/api/events/{eid}")
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertEqual(body["id"], eid)
        self.assertEqual(body["content"], "session opened")

    async def test_get_event_404(self):
        resp = await self.client.get("/api/events/999999")
        self.assertEqual(resp.status_code, 404)

    # ---- GET /api/sessions/<id>/events ----

    async def test_list_session_events_subroute(self):
        await self.client.post("/api/events", json={
            "session_id": self.session_id, "role": "user", "kind": "chat",
            "content": "sub",
        })
        resp = await self.client.get(f"/api/sessions/{self.session_id}/events")
        self.assertEqual(resp.status_code, 200)
        rows = await resp.get_json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["content"], "sub")

    # ---- GET /api/sessions/<id>/events/latest_id ----

    async def test_latest_event_id_empty(self):
        """No events → latest_id is null (not 404)."""
        resp = await self.client.get(f"/api/sessions/{self.session_id}/events/latest_id")
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertIsNone(body["latest_event_id"])

    async def test_latest_event_id_after_inserts(self):
        """After inserting 3 events, latest_id == max(id)."""
        for i in range(3):
            await self.client.post("/api/events", json={
                "session_id": self.session_id, "role": "user", "kind": "chat",
                "content": f"msg {i}",
            })
        resp = await self.client.get(f"/api/sessions/{self.session_id}/events/latest_id")
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        # The list endpoint should give the same max
        list_resp = await self.client.get(f"/api/sessions/{self.session_id}/events")
        rows = await list_resp.get_json()
        self.assertEqual(body["latest_event_id"], rows[-1]["id"])
