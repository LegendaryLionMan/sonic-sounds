"""tests/test_handlers_decisions_extra.py — expanded Day 5 review tests for /api/decisions.

Adds ~25 tests covering edge cases the original 17 missed:
- PATCH with all three fields, locked_at monotonicity
- code with same album: multiple rows OK
- All tier values
- Methods not allowed
- Content-Type edge cases
- Unicode content + rationale
- Long content (10KB)
- Concurrent inserts
- Filter combinations
- Empty body / no Content-Type
- Decision <-> events isolation (no cross-API leak)
"""
import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _isolate_tempdb():
    tmpdir = Path(tempfile.mkdtemp(prefix="sonic-studio-test-decisions-extra-"))
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


def _wipe_decisions():
    from db import connection as db_conn
    conn = db_conn.open_db()
    try:
        conn.execute("DELETE FROM decisions")
        conn.commit()
    finally:
        db_conn.close_db()


class TestDecisionsEdgeCases(unittest.IsolatedAsyncioTestCase):
    """Expanded coverage — decisions edge cases & CRUD matrix."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir, cls.tempdb = _isolate_tempdb()
        from db import migrations, albums as db_albums, sessions as db_sessions
        migrations.bootstrap_initial_migration(cls.tempdb)
        migrations.run_migrations(cls.tempdb)
        db_albums.create_artist("a1", "Artist", db_path=cls.tempdb)
        for i in range(1, 5):
            db_albums.create_album(f"al{i}", f"Album {i}", "a1", db_path=cls.tempdb)
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
        await asyncio.to_thread(_wipe_decisions)

    # ---- All tier values ----

    async def test_all_tiers_accepted(self):
        for tier in ("mandatory", "recommended", "extra"):
            resp = await self.client.post("/api/decisions", json={
                "code": f"{tier[0].upper()}01", "tier": tier,
                "answer": f"answer for {tier}",
            })
            self.assertEqual(resp.status_code, 201, f"tier={tier} rejected")
            body = await resp.get_json()
            self.assertEqual(body["tier"], tier)

    async def test_invalid_tier_rejected_with_helpful_message(self):
        resp = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "optional",
        })
        self.assertEqual(resp.status_code, 400)
        body = await resp.get_json()
        self.assertIn("tier", body["error"])
        # The error message should mention the valid tiers
        self.assertIn("mandatory", body["error"])

    # ---- Multiple rows same code ----

    async def test_same_code_multiple_walks_appends(self):
        """db/decisions.py comment: 'We append rather than upsert —
        multiple walks may produce multiple rows for the same code.'"""
        for i in range(3):
            r = await self.client.post("/api/decisions", json={
                "code": "M01", "tier": "mandatory",
                "answer": f"walk {i}",
                "album_id": "al1",
            })
            self.assertEqual(r.status_code, 201)
        resp = await self.client.get("/api/decisions?code=M01&album=al1")
        rows = await resp.get_json()
        self.assertEqual(len(rows), 3)
        self.assertEqual([r["answer"] for r in rows], ["walk 0", "walk 1", "walk 2"])

    # ---- PATCH locked_at monotonicity ----

    async def test_locked_at_bumps_on_each_patch(self):
        create = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory", "answer": "v1",
        })
        body1 = await create.get_json()
        locked1 = body1["locked_at"]

        # Sleep briefly so timestamps differ
        await asyncio.sleep(0.1)

        patch = await self.client.patch(
            f"/api/decisions/{body1['id']}", json={"answer": "v2"}
        )
        body2 = await patch.get_json()
        locked2 = body2["locked_at"]
        self.assertNotEqual(locked1, locked2)
        # SQLite datetime('now') has second precision; just verify it moved forward
        self.assertGreaterEqual(locked2, locked1)

        await asyncio.sleep(0.1)
        patch3 = await self.client.patch(
            f"/api/decisions/{body1['id']}", json={"rationale": "because"}
        )
        body3 = await patch3.get_json()
        self.assertGreaterEqual(body3["locked_at"], locked2)

    async def test_patch_all_three_fields(self):
        create = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory", "answer": "old",
        })
        did = (await create.get_json())["id"]
        resp = await self.client.patch(f"/api/decisions/{did}", json={
            "answer": "new answer",
            "rationale": "new rationale",
            "source_doc": "v3.4-DAY5.md",
        })
        body = await resp.get_json()
        self.assertEqual(body["answer"], "new answer")
        self.assertEqual(body["rationale"], "new rationale")
        self.assertEqual(body["source_doc"], "v3.4-DAY5.md")

    async def test_patch_with_only_answer_clears_rationale_no_op(self):
        """PATCH with answer only should NOT clear rationale or source_doc."""
        create = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory",
            "answer": "v1", "rationale": "kept",
            "source_doc": "doc.md",
        })
        body = await create.get_json()
        resp = await self.client.patch(f"/api/decisions/{body['id']}", json={
            "answer": "v2",
        })
        body2 = await resp.get_json()
        self.assertEqual(body2["answer"], "v2")
        self.assertEqual(body2["rationale"], "kept")
        self.assertEqual(body2["source_doc"], "doc.md")

    async def test_patch_with_explicit_null_clears_field(self):
        """PATCH with explicit null answer is treated as 'clear this field'.

        This is a deliberate distinction from omitting the key
        (which means 'don't touch'). An explicit null is meaningful:
        the user is saying "this field should now be empty."
        """
        create = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory", "answer": "kept",
        })
        body = await create.get_json()
        resp = await self.client.patch(f"/api/decisions/{body['id']}", json={
            "answer": None,
        })
        body2 = await resp.get_json()
        # Explicit null clears the answer
        self.assertIsNone(body2["answer"])

    async def test_patch_omitted_field_does_not_clear(self):
        """PATCH without 'answer' key leaves existing answer intact."""
        create = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory", "answer": "kept",
            "rationale": "r1",
        })
        body = await create.get_json()
        resp = await self.client.patch(f"/api/decisions/{body['id']}", json={
            "rationale": "r2",
        })
        body2 = await resp.get_json()
        self.assertEqual(body2["answer"], "kept")
        self.assertEqual(body2["rationale"], "r2")

    # ---- Filter combinations ----

    async def test_filter_album_plus_tier(self):
        await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory", "album_id": "al1",
        })
        await self.client.post("/api/decisions", json={
            "code": "R01", "tier": "recommended", "album_id": "al1",
        })
        await self.client.post("/api/decisions", json={
            "code": "M02", "tier": "mandatory", "album_id": "al2",
        })
        resp = await self.client.get("/api/decisions?album=al1&tier=mandatory")
        rows = await resp.get_json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["code"], "M01")

    async def test_filter_code_exact_match(self):
        """?code= filters by exact match — M01 does NOT match M010."""
        await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory",
        })
        await self.client.post("/api/decisions", json={
            "code": "M010", "tier": "mandatory",  # different code
        })
        resp = await self.client.get("/api/decisions?code=M01")
        rows = await resp.get_json()
        # M01 matches; M010 does not (SQL is `code = ?`, exact)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["code"], "M01")

    async def test_filter_session_returns_only_that_session(self):
        await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory",
            "session_id": self.session_id, "album_id": "al1",
        })
        await self.client.post("/api/decisions", json={
            "code": "M02", "tier": "mandatory",
            "session_id": "different-session", "album_id": "al1",
        })
        resp = await self.client.get(f"/api/decisions?session={self.session_id}")
        rows = await resp.get_json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["code"], "M01")

    # ---- Methods not allowed ----

    async def test_put_on_decisions_collection(self):
        resp = await self.client.put("/api/decisions", json={})
        self.assertEqual(resp.status_code, 405)

    async def test_post_on_single_decision(self):
        """POST /api/decisions/<id> is not registered — 405."""
        resp = await self.client.post("/api/decisions/1", json={})
        self.assertEqual(resp.status_code, 405)

    async def test_get_decision_invalid_id_string(self):
        """Quart's <int:decision_id> rejects non-integer paths → 404."""
        resp = await self.client.get("/api/decisions/not-an-int")
        self.assertEqual(resp.status_code, 404)

    # ---- Content-Type edge cases ----

    async def test_post_text_plain_returns_400(self):
        resp = await self.client.post(
            "/api/decisions", data="not json",
            headers={"Content-Type": "text/plain"},
        )
        self.assertEqual(resp.status_code, 400)

    async def test_post_empty_body_returns_400(self):
        resp = await self.client.post("/api/decisions", data="")
        self.assertEqual(resp.status_code, 400)

    # ---- Unicode + long content ----

    async def test_unicode_answer_and_rationale(self):
        resp = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory",
            "question": "Qual é o título?",
            "answer": "Meio da Noite 🌙",
            "rationale": "ブレインストーミングの結論 🎵",
        })
        body = await resp.get_json()
        self.assertEqual(body["question"], "Qual é o título?")
        self.assertEqual(body["answer"], "Meio da Noite 🌙")
        self.assertEqual(body["rationale"], "ブレインストーミングの結論 🎵")

    async def test_long_rationale_round_trip(self):
        rationale = "rationale " * 1000  # ~11KB
        resp = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory",
            "answer": "x", "rationale": rationale,
        })
        body = await resp.get_json()
        self.assertEqual(len(body["rationale"]), len(rationale))

    # ---- Concurrency ----

    async def test_concurrent_decisions_unique_ids(self):
        async def post_one(i):
            r = await self.client.post("/api/decisions", json={
                "code": f"D{i:03d}", "tier": "recommended",
                "album_id": "al1",
            })
            return (await r.get_json())["id"]
        ids = await asyncio.gather(*[post_one(i) for i in range(15)])
        self.assertEqual(len(set(ids)), 15)

    async def test_concurrent_patches_one_decision(self):
        """Last writer wins; no corruption, no 500s."""
        create = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory", "answer": "v0",
        })
        did = (await create.get_json())["id"]
        async def patch_one(i):
            return await self.client.patch(
                f"/api/decisions/{did}", json={"answer": f"v{i}"}
            )
        results = await asyncio.gather(*[patch_one(i) for i in range(10)])
        for r in results:
            self.assertEqual(r.status_code, 200)

    # ---- Cross-API isolation ----

    async def test_decisions_endpoint_does_not_leak_events(self):
        """Decisions and events are stored separately. Listing decisions
        shouldn't include any events."""
        await self.client.post("/api/events", json={
            "session_id": self.session_id, "role": "user", "kind": "chat",
            "content": "this is an event, not a decision",
        })
        resp = await self.client.get("/api/decisions")
        self.assertEqual(resp.status_code, 200)
        rows = await resp.get_json()
        # No events should be in the decisions list
        self.assertEqual(rows, [])

    async def test_decision_response_has_no_payload_field(self):
        """Decisions have NO 'payload' column (events do). The schema is
        different and the handler should NOT add a payload field."""
        resp = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory", "answer": "x",
        })
        body = await resp.get_json()
        self.assertNotIn("payload", body)
        self.assertNotIn("payload_json", body)

    # ---- DELETE edge cases ----

    async def test_delete_returns_no_body(self):
        create = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory",
        })
        did = (await create.get_json())["id"]
        resp = await self.client.delete(f"/api/decisions/{did}")
        self.assertEqual(resp.status_code, 204)
        # 204 responses must have empty body
        body = await resp.get_data()
        self.assertEqual(body, b"")
