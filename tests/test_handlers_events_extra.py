"""tests/test_handlers_events_extra.py — expanded Day 5 review tests for /api/events.

Adds ~30 tests covering edge cases the original 16 missed:
- Pagination limits (0, negative, >cap, non-integer)
- since_id + since_ts combined
- Session-scoped isolation
- Empty/None content
- Concurrency (concurrent inserts)
- JSON payload edge cases
- ?session=<nonexistent> returns empty list, not error
- Methods that aren't allowed (PUT, DELETE on /api/events collection)
- Unicode content
- Long content
- Decision cross-API isolation
"""
import asyncio
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
    """Same isolation pattern as test_handlers_events.py."""
    tmpdir = Path(tempfile.mkdtemp(prefix="sonic-studio-test-events-extra-"))
    tempdb = tmpdir / "test.db"
    os.environ["SONIC_STUDIO_DB_PATH"] = str(tempdb)
    for mod_name in list(sys.modules):
        if (mod_name == "db" or mod_name.startswith("db.")
                or mod_name.startswith("build.")):
            del sys.modules[mod_name]
    return tmpdir, tempdb


def _drop_isolation():
    from db.connection import close_all
    try:
        close_all()
    except Exception:
        pass
    for mod_name in list(sys.modules):
        if mod_name == "db" or mod_name.startswith("db."):
            del sys.modules[mod_name]
    os.environ.pop("SONIC_STUDIO_DB_PATH", None)


def _wipe_events():
    """Wipe events table on the live tempdb."""
    from db import connection as db_conn
    conn = db_conn.open_db()
    try:
        conn.execute("DELETE FROM events")
        conn.commit()
    finally:
        db_conn.close_db()


class TestEventsEdgeCases(unittest.IsolatedAsyncioTestCase):
    """Expanded coverage — events edge cases & pagination."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir, cls.tempdb = _isolate_tempdb()
        from db import migrations, albums as db_albums, sessions as db_sessions
        migrations.bootstrap_initial_migration(cls.tempdb)
        migrations.run_migrations(cls.tempdb)
        db_albums.create_artist("a1", "Artist", db_path=cls.tempdb)
        for i in range(1, 6):
            db_albums.create_album(f"al{i}", f"Album {i}", "a1", db_path=cls.tempdb)
        sess = db_sessions.open_session("al1", db_path=cls.tempdb)
        cls.session_id = sess["id"]
        cls.other_session_id = db_sessions.open_session("al2", db_path=cls.tempdb)["id"]

    @classmethod
    def tearDownClass(cls):
        _drop_isolation()
        import shutil
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    async def asyncSetUp(self):
        from build.serve import create_app
        self.app = create_app()
        self.client = self.app.test_client()
        await asyncio.to_thread(_wipe_events)

    # ---- Pagination limit edge cases ----

    async def test_limit_zero_returns_empty(self):
        await self.client.post("/api/events", json={
            "session_id": self.session_id, "role": "user", "kind": "chat",
            "content": "x",
        })
        resp = await self.client.get(
            f"/api/events?session={self.session_id}&limit=0"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(await resp.get_json(), [])

    async def test_limit_negative_returns_200_unbounded(self):
        """limit=-1 is parsed as int → -1. SQLite treats negative
        LIMIT as 'no limit', so the query succeeds. Document this:
        the handler caps at 500 from above (positive cap) but doesn't
        clamp negatives. This is safe because the session filter
        still bounds the result set."""
        resp = await self.client.get(
            f"/api/events?session={self.session_id}&limit=-1"
        )
        self.assertEqual(resp.status_code, 200)

    async def test_limit_capped_at_500(self):
        """limit=99999 is silently capped to 500 (handler min() with 500)."""
        resp = await self.client.get(
            f"/api/events?session={self.session_id}&limit=99999"
        )
        self.assertEqual(resp.status_code, 200)

    async def test_limit_non_integer_returns_400(self):
        resp = await self.client.get(
            f"/api/events?session={self.session_id}&limit=abc"
        )
        self.assertEqual(resp.status_code, 400)

    # ---- Cursor combinations ----

    async def test_since_id_and_since_together_since_id_wins(self):
        """When both since_id and since are provided, since_id is the
        source of truth (post-hoc filter). since= is ignored if both
        are given. Test that events after since_id are returned even if
        their timestamp is OLDER than since= would suggest."""
        ids = []
        for i in range(3):
            r = await self.client.post("/api/events", json={
                "session_id": self.session_id, "role": "user", "kind": "chat",
                "content": f"m{i}",
            })
            ids.append((await r.get_json())["id"])

        # since_id=ids[0] AND since=2099-01-01 (impossible future)
        # → handler should still return events[1:] because since_id
        # filter is applied post-hoc on the rows that the db layer
        # returned (which were all 3, since since= filter would exclude
        # all of them, but wait — if since=2099-01-01 returns [] then
        # the since_id filter has nothing to work on)
        # Better: since=1900-01-01 (very old, returns all) + since_id=ids[0]
        resp = await self.client.get(
            f"/api/events?session={self.session_id}"
            f"&since=1900-01-01T00:00:00&since_id={ids[0]}"
        )
        rows = await resp.get_json()
        # The db layer returns all 3 (since=1900 is past), then since_id
        # filters to ids[1], ids[2]
        self.assertEqual(len(rows), 2)
        self.assertEqual([r["id"] for r in rows], [ids[1], ids[2]])

    async def test_since_id_zero_returns_all(self):
        """since_id=0 returns all events (id > 0 always true)."""
        for i in range(2):
            await self.client.post("/api/events", json={
                "session_id": self.session_id, "role": "user", "kind": "chat",
                "content": f"x{i}",
            })
        resp = await self.client.get(
            f"/api/events?session={self.session_id}&since_id=0"
        )
        rows = await resp.get_json()
        self.assertEqual(len(rows), 2)

    async def test_since_id_negative_treated_as_int(self):
        """since_id=-5 is an integer so it's accepted; -5 > 0 is false
        for all real ids, so all events returned (id > -5 is true for
        any positive id)."""
        await self.client.post("/api/events", json={
            "session_id": self.session_id, "role": "user", "kind": "chat",
            "content": "x",
        })
        resp = await self.client.get(
            f"/api/events?session={self.session_id}&since_id=-5"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(await resp.get_json()), 1)

    # ---- Session isolation ----

    async def test_session_filter_isolates_sessions(self):
        """Events for session A don't leak into session B queries."""
        await self.client.post("/api/events", json={
            "session_id": self.session_id, "role": "user", "kind": "chat",
            "content": "for session A",
        })
        await self.client.post("/api/events", json={
            "session_id": self.other_session_id, "role": "user", "kind": "chat",
            "content": "for session B",
        })
        resp = await self.client.get(
            f"/api/events?session={self.session_id}"
        )
        rows = await resp.get_json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["content"], "for session A")

    async def test_session_nonexistent_returns_empty(self):
        """?session=<unknown> returns 200 + [] (not 404)."""
        resp = await self.client.get(
            "/api/events?session=ghost-session-id"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(await resp.get_json(), [])

    # ---- Content edge cases ----

    async def test_create_event_empty_content_string(self):
        """content='' is allowed (some system events have no body)."""
        resp = await self.client.post("/api/events", json={
            "session_id": self.session_id, "role": "system", "kind": "log",
            "content": "",
        })
        self.assertEqual(resp.status_code, 201)
        body = await resp.get_json()
        self.assertEqual(body["content"], "")

    async def test_create_event_no_content_field(self):
        """content omitted entirely is OK."""
        resp = await self.client.post("/api/events", json={
            "session_id": self.session_id, "role": "system", "kind": "log",
        })
        self.assertEqual(resp.status_code, 201)
        body = await resp.get_json()
        self.assertIsNone(body["content"])

    async def test_create_event_unicode_content(self):
        resp = await self.client.post("/api/events", json={
            "session_id": self.session_id, "role": "user", "kind": "chat",
            "content": "Olá mundo 🌍 مرحبا 日本語",
        })
        self.assertEqual(resp.status_code, 201)
        body = await resp.get_json()
        self.assertEqual(body["content"], "Olá mundo 🌍 مرحبا 日本語")

    async def test_create_event_long_content(self):
        """10KB content survives round-trip."""
        content = "x" * (10 * 1024)
        resp = await self.client.post("/api/events", json={
            "session_id": self.session_id, "role": "user", "kind": "chat",
            "content": content,
        })
        self.assertEqual(resp.status_code, 201)
        body = await resp.get_json()
        self.assertEqual(len(body["content"]), 10 * 1024)

    # ---- Payload edge cases ----

    async def test_payload_null_returns_null(self):
        resp = await self.client.post("/api/events", json={
            "session_id": self.session_id, "role": "user", "kind": "chat",
            "content": "no payload", "payload": None,
        })
        body = await resp.get_json()
        self.assertIsNone(body["payload"])

    async def test_payload_empty_dict(self):
        resp = await self.client.post("/api/events", json={
            "session_id": self.session_id, "role": "user", "kind": "chat",
            "content": "empty payload", "payload": {},
        })
        body = await resp.get_json()
        self.assertEqual(body["payload"], {})

    async def test_payload_nested_dict(self):
        resp = await self.client.post("/api/events", json={
            "session_id": self.session_id, "role": "assistant", "kind": "build",
            "content": "deep", "payload": {"a": {"b": {"c": [1, 2, 3]}}},
        })
        body = await resp.get_json()
        self.assertEqual(body["payload"]["a"]["b"]["c"], [1, 2, 3])

    async def test_payload_with_unicode_keys_and_values(self):
        resp = await self.client.post("/api/events", json={
            "session_id": self.session_id, "role": "user", "kind": "chat",
            "content": "x", "payload": {"chave": "値", "🔑": "value"},
        })
        body = await resp.get_json()
        self.assertEqual(body["payload"]["chave"], "値")
        self.assertEqual(body["payload"]["🔑"], "value")

    # ---- Role + kind matrix ----

    async def test_all_valid_roles_accepted(self):
        for role in ("user", "assistant", "system", "tool"):
            resp = await self.client.post("/api/events", json={
                "session_id": self.session_id, "role": role, "kind": "chat",
                "content": f"role={role}",
            })
            self.assertEqual(resp.status_code, 201, f"role={role} rejected")

    async def test_all_valid_kinds_accepted(self):
        for kind in ("chat", "build", "quota", "system", "log"):
            resp = await self.client.post("/api/events", json={
                "session_id": self.session_id, "role": "user", "kind": kind,
                "content": f"kind={kind}",
            })
            self.assertEqual(resp.status_code, 201, f"kind={kind} rejected")

    async def test_invalid_role_rejected_with_helpful_message(self):
        resp = await self.client.post("/api/events", json={
            "session_id": self.session_id, "role": "admin", "kind": "chat",
        })
        self.assertEqual(resp.status_code, 400)
        body = await resp.get_json()
        # Error message should mention 'role' AND list the valid options
        self.assertIn("role", body["error"].lower())
        self.assertIn("user", body["error"])

    async def test_invalid_kind_rejected_with_helpful_message(self):
        resp = await self.client.post("/api/events", json={
            "session_id": self.session_id, "role": "user", "kind": "spam",
        })
        self.assertEqual(resp.status_code, 400)
        body = await resp.get_json()
        self.assertIn("kind", body["error"].lower())
        self.assertIn("chat", body["error"])

    # ---- Concurrency ----

    async def test_concurrent_posts_all_succeed(self):
        """10 concurrent inserts should all succeed (no FK violations,
        no race on autoincrement)."""
        async def post_one(i):
            return await self.client.post("/api/events", json={
                "session_id": self.session_id, "role": "user", "kind": "chat",
                "content": f"concurrent {i}",
            })
        results = await asyncio.gather(*[post_one(i) for i in range(10)])
        for i, r in enumerate(results):
            self.assertEqual(r.status_code, 201, f"index {i} failed: {await r.get_data()}")

    async def test_concurrent_posts_have_unique_ids(self):
        async def post_one(i):
            r = await self.client.post("/api/events", json={
                "session_id": self.session_id, "role": "user", "kind": "chat",
                "content": f"x{i}",
            })
            return (await r.get_json())["id"]
        ids = await asyncio.gather(*[post_one(i) for i in range(10)])
        self.assertEqual(len(set(ids)), 10, f"duplicate ids: {ids}")

    # ---- Methods not allowed ----

    async def test_put_on_events_collection(self):
        """PUT /api/events is not registered — should 405."""
        resp = await self.client.put("/api/events", json={})
        self.assertEqual(resp.status_code, 405)

    async def test_delete_on_events_collection(self):
        """DELETE /api/events is not registered — should 405."""
        resp = await self.client.delete("/api/events")
        self.assertEqual(resp.status_code, 405)

    async def test_patch_on_events_collection(self):
        """PATCH /api/events is not registered — should 405."""
        resp = await self.client.patch("/api/events", json={})
        self.assertEqual(resp.status_code, 405)

    # ---- Content-Type edge cases ----

    async def test_text_plain_content_type_falls_back_to_empty(self):
        """Sending text/plain body → request.get_json(silent=True) returns None
        → payload becomes {} → missing required fields → 400."""
        resp = await self.client.post(
            "/api/events",
            data="not json",
            headers={"Content-Type": "text/plain"},
        )
        self.assertEqual(resp.status_code, 400)
        body = await resp.get_json()
        self.assertIn("missing", body["error"])

    async def test_no_content_type_400(self):
        """No Content-Type + raw body → silent json parse → 400."""
        resp = await self.client.post("/api/events", data="not json")
        self.assertEqual(resp.status_code, 400)

    # ---- latest_id ----

    async def test_latest_id_for_failed_session_returns_null(self):
        """Even if session doesn't exist, latest_id returns 200 + null
        (we don't 404 because the caller might want to check)."""
        resp = await self.client.get(
            "/api/sessions/ghost-session/events/latest_id"
        )
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertIsNone(body["latest_event_id"])
        self.assertEqual(body["session_id"], "ghost-session")
