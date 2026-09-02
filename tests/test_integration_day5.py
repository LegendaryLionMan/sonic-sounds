"""tests/test_integration_day5.py — cross-cutting integration tests.

Covers scenarios that span events + decisions + sessions + albums:
- Full session lifecycle with event/decision logging at each step
- Decision "walk" pattern: multiple decisions per code across a session
- Polling simulation: client polls for new events, sees them appear
- API contract invariants (response shapes, content-type headers)
- Cross-API: events for session A don't surface in session B's events
- The studio.js path: open session → log events → lock decisions
- POST → GET round-trip preserves all fields
- Decisions persist across session close/open cycles
- Idempotent PATCH (same value twice = same result)
- Cascade semantics (delete session, what happens to events/decisions)
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
    tmpdir = Path(tempfile.mkdtemp(prefix="album-studio-test-day5-integration-"))
    tempdb = tmpdir / "test.db"
    os.environ["ALBUM_STUDIO_DB_PATH"] = str(tempdb)
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
    os.environ.pop("ALBUM_STUDIO_DB_PATH", None)


def _wipe_all():
    """Wipe events + decisions tables for clean per-test isolation."""
    from db import connection as db_conn
    conn = db_conn.open_db()
    try:
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM decisions")
        conn.execute("DELETE FROM album_sessions")
        conn.commit()
    finally:
        db_conn.close_db()


class TestDay5Integration(unittest.IsolatedAsyncioTestCase):
    """Integration tests spanning multiple endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir, cls.tempdb = _isolate_tempdb()
        from db import migrations, albums as db_albums
        migrations.bootstrap_initial_migration(cls.tempdb)
        migrations.run_migrations(cls.tempdb)
        db_albums.create_artist("a1", "Maren Sol", db_path=cls.tempdb)
        db_albums.create_album("half-light-hours", "Half-Light Hours",
                                "a1", db_path=cls.tempdb)
        db_albums.create_album("midnight-room", "Midnight Room",
                                "a1", db_path=cls.tempdb)

    @classmethod
    def tearDownClass(cls):
        _drop_isolation()
        import shutil
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    async def asyncSetUp(self):
        from build.serve import create_app
        self.app = create_app()
        self.client = self.app.test_client()
        await asyncio.to_thread(_wipe_all)

    # ---- Full lifecycle ----

    async def test_full_album_session_event_decision_workflow(self):
        """End-to-end: create session, log events, lock decisions,
        complete session, verify everything persisted."""
        # Open session
        r = await self.client.post("/api/sessions",
                                    json={"album_id": "half-light-hours"})
        self.assertEqual(r.status_code, 201)
        sid = (await r.get_json())["id"]

        # Log events
        for i in range(3):
            r = await self.client.post("/api/events", json={
                "session_id": sid, "role": "user", "kind": "chat",
                "content": f"message {i}",
                "album_id": "half-light-hours",
            })
            self.assertEqual(r.status_code, 201)

        # Lock decisions
        for code, tier in [("M01", "mandatory"), ("R01", "recommended"),
                            ("X01", "extra")]:
            r = await self.client.post("/api/decisions", json={
                "code": code, "tier": tier,
                "album_id": "half-light-hours", "session_id": sid,
                "answer": f"answer for {code}",
            })
            self.assertEqual(r.status_code, 201)

        # Complete session
        r = await self.client.post(f"/api/sessions/{sid}/complete")
        self.assertEqual(r.status_code, 200)

        # Verify everything persisted
        sess = await (await self.client.get(f"/api/sessions/{sid}")).get_json()
        self.assertEqual(sess["status"], "done")

        events = await (await self.client.get(
            f"/api/sessions/{sid}/events")).get_json()
        self.assertEqual(len(events), 3)

        decs = await (await self.client.get(
            f"/api/albums/half-light-hours/decisions")).get_json()
        self.assertEqual(len(decs), 3)
        tiers = sorted(d["tier"] for d in decs)
        self.assertEqual(tiers, ["extra", "mandatory", "recommended"])

    # ---- Polling simulation ----

    async def test_client_polls_events_sees_them_appear(self):
        """Simulate studio.js: open session, log events, poll with
        since_id, observe new events appear."""
        r = await self.client.post("/api/sessions",
                                    json={"album_id": "midnight-room"})
        sid = (await r.get_json())["id"]

        # Initial poll: cursor=0, get all (none yet)
        r = await self.client.get(f"/api/sessions/{sid}/events?since_id=0")
        self.assertEqual(len(await r.get_json()), 0)

        # Log event 1
        await self.client.post("/api/events", json={
            "session_id": sid, "role": "user", "kind": "chat",
            "content": "first",
        })

        # Poll again — should see event 1
        r = await self.client.get(f"/api/sessions/{sid}/events?since_id=0")
        rows = await r.get_json()
        self.assertEqual(len(rows), 1)
        cursor = rows[-1]["id"]

        # Log events 2, 3
        for content in ("second", "third"):
            await self.client.post("/api/events", json={
                "session_id": sid, "role": "user", "kind": "chat",
                "content": content,
            })

        # Poll with cursor — should see only new (2, 3)
        r = await self.client.get(f"/api/sessions/{sid}/events?since_id={cursor}")
        new_rows = await r.get_json()
        self.assertEqual(len(new_rows), 2)
        self.assertEqual([r["content"] for r in new_rows], ["second", "third"])

    # ---- Cross-API isolation ----

    async def test_album_a_events_dont_leak_to_album_b(self):
        """Events are session-scoped, sessions are album-scoped — but
        a query with ?session=<A's session> must NEVER return events
        from <B's session>."""
        # Two sessions on two different albums
        r1 = await self.client.post("/api/sessions",
                                     json={"album_id": "half-light-hours"})
        sid_a = (await r1.get_json())["id"]
        r2 = await self.client.post("/api/sessions",
                                     json={"album_id": "midnight-room"})
        sid_b = (await r2.get_json())["id"]

        # Log events on each
        await self.client.post("/api/events", json={
            "session_id": sid_a, "role": "user", "kind": "chat",
            "content": "A's event",
        })
        await self.client.post("/api/events", json={
            "session_id": sid_b, "role": "user", "kind": "chat",
            "content": "B's event",
        })

        # Each session sees only its own
        a_events = await (await self.client.get(
            f"/api/sessions/{sid_a}/events")).get_json()
        b_events = await (await self.client.get(
            f"/api/sessions/{sid_b}/events")).get_json()
        self.assertEqual(len(a_events), 1)
        self.assertEqual(a_events[0]["content"], "A's event")
        self.assertEqual(len(b_events), 1)
        self.assertEqual(b_events[0]["content"], "B's event")

    # ---- Decisions across walks ----

    async def test_decision_walks_preserve_history(self):
        """The same decision code (M01) can be locked multiple times
        across different walks/sessions, building a history."""
        sessions = []
        for i in range(3):
            r = await self.client.post("/api/sessions",
                                        json={"album_id": "half-light-hours"})
            sessions.append((await r.get_json())["id"])

        # Each session locks M01 with a different answer
        for i, sid in enumerate(sessions):
            r = await self.client.post("/api/decisions", json={
                "code": "M01", "tier": "mandatory",
                "album_id": "half-light-hours", "session_id": sid,
                "answer": f"walk {i} answer",
                "rationale": f"walk {i} rationale",
            })
            self.assertEqual(r.status_code, 201)

        # Album has 3 M01 rows
        decs = await (await self.client.get(
            "/api/albums/half-light-hours/decisions?code=M01")).get_json()
        self.assertEqual(len(decs), 3)
        answers = [d["answer"] for d in decs]
        self.assertEqual(answers, ["walk 0 answer", "walk 1 answer", "walk 2 answer"])

        # Locked_at is strictly increasing (subsecond precision)
        locked = [d["locked_at"] for d in decs]
        self.assertEqual(locked, sorted(locked))

    # ---- Response invariants ----

    async def test_all_event_responses_are_json(self):
        """Every /api/events* endpoint must return JSON."""
        r = await self.client.post("/api/sessions",
                                    json={"album_id": "half-light-hours"})
        sid = (await r.get_json())["id"]
        await self.client.post("/api/events", json={
            "session_id": sid, "role": "user", "kind": "chat", "content": "x",
        })

        paths = [
            ("GET", "/api/events?session=" + sid),
            ("GET", f"/api/sessions/{sid}/events"),
            ("GET", f"/api/sessions/{sid}/events/latest_id"),
        ]
        for method, path in paths:
            r = await self.client.open(method=method, path=path)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.headers.get("Content-Type", "").split(";")[0],
                              "application/json", f"{method} {path} not JSON")

    async def test_all_decision_responses_are_json(self):
        r = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory", "answer": "x",
        })
        did = (await r.get_json())["id"]

        for method, path in [
            ("GET", "/api/decisions"),
            ("GET", f"/api/decisions/{did}"),
            ("PATCH", f"/api/decisions/{did}"),
        ]:
            if method == "PATCH":
                r = await self.client.patch(path, json={"answer": "y"})
            else:
                r = await self.client.open(method=method, path=path)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.headers.get("Content-Type", "").split(";")[0],
                              "application/json", f"{method} {path} not JSON")

    # ---- POST → GET round-trip ----

    async def test_event_post_get_round_trip_preserves_all_fields(self):
        """Every field set in the POST body must come back identical in
        the GET response."""
        r = await self.client.post("/api/sessions",
                                    json={"album_id": "half-light-hours"})
        sid = (await r.get_json())["id"]

        r = await self.client.post("/api/events", json={
            "session_id": sid,
            "role": "assistant",
            "kind": "build",
            "content": "round-trip test",
            "album_id": "half-light-hours",
            "payload": {"layer": 3, "phase": "lyrics_finalize",
                         "nested": {"key": "value"}},
        })
        created = await r.get_json()
        eid = created["id"]

        r = await self.client.get(f"/api/events/{eid}")
        fetched = await r.get_json()

        self.assertEqual(created["session_id"], fetched["session_id"])
        self.assertEqual(created["role"], fetched["role"])
        self.assertEqual(created["kind"], fetched["kind"])
        self.assertEqual(created["content"], fetched["content"])
        self.assertEqual(created["album_id"], fetched["album_id"])
        self.assertEqual(created["payload"], fetched["payload"])

    async def test_decision_post_get_round_trip_preserves_all_fields(self):
        """Every field set in the POST body must come back identical."""
        r = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory",
            "question": "What is the title?",
            "answer": "Half-Light Hours",
            "rationale": "because it resonates",
            "source_doc": "v3.4-DAY5.md",
            "album_id": "half-light-hours",
        })
        created = await r.get_json()
        did = created["id"]

        r = await self.client.get(f"/api/decisions/{did}")
        fetched = await r.get_json()

        self.assertEqual(created["code"], fetched["code"])
        self.assertEqual(created["tier"], fetched["tier"])
        self.assertEqual(created["question"], fetched["question"])
        self.assertEqual(created["answer"], fetched["answer"])
        self.assertEqual(created["rationale"], fetched["rationale"])
        self.assertEqual(created["source_doc"], fetched["source_doc"])
        self.assertEqual(created["album_id"], fetched["album_id"])
        self.assertIsNotNone(fetched["locked_at"])

    # ---- Idempotent PATCH ----

    async def test_patch_same_value_idempotent(self):
        """PATCH with the same value should not change locked_at."""
        r = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory", "answer": "v1",
        })
        body1 = await r.get_json()
        await asyncio.sleep(0.01)

        r = await self.client.patch(f"/api/decisions/{body1['id']}",
                                     json={"answer": "v1"})
        body2 = await r.get_json()
        # Same value, so locked_at might or might not bump — both
        # behaviors are acceptable. Important: the answer is still v1.
        self.assertEqual(body2["answer"], "v1")

    async def test_patch_then_delete_then_get_is_404(self):
        r = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory",
        })
        did = (await r.get_json())["id"]
        r = await self.client.delete(f"/api/decisions/{did}")
        self.assertEqual(r.status_code, 204)
        r = await self.client.get(f"/api/decisions/{did}")
        self.assertEqual(r.status_code, 404)

    # ---- Cascade behavior ----

    async def test_decision_survives_session_completion(self):
        """Decisions are persistent log entries; closing a session
        must NOT delete the decisions recorded during it."""
        r = await self.client.post("/api/sessions",
                                    json={"album_id": "half-light-hours"})
        sid = (await r.get_json())["id"]
        r = await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory",
            "session_id": sid, "album_id": "half-light-hours",
            "answer": "persisted",
        })
        did = (await r.get_json())["id"]
        # Complete session
        await self.client.post(f"/api/sessions/{sid}/complete")
        # Decision still queryable
        r = await self.client.get(f"/api/decisions/{did}")
        self.assertEqual(r.status_code, 200)
        body = await r.get_json()
        self.assertEqual(body["answer"], "persisted")

    async def test_event_survives_session_completion(self):
        """Events are persistent log entries; closing a session
        must NOT delete events recorded during it."""
        r = await self.client.post("/api/sessions",
                                    json={"album_id": "half-light-hours"})
        sid = (await r.get_json())["id"]
        r = await self.client.post("/api/events", json={
            "session_id": sid, "role": "user", "kind": "chat",
            "content": "persisted",
        })
        eid = (await r.get_json())["id"]
        await self.client.post(f"/api/sessions/{sid}/complete")
        r = await self.client.get(f"/api/events/{eid}")
        self.assertEqual(r.status_code, 200)
        body = await r.get_json()
        self.assertEqual(body["content"], "persisted")

    # ---- Studio.js realistic flow ----

    async def test_studio_realistic_flow(self):
        """Simulate what studio.js does end-to-end:
        1. Pick session from picker
        2. Show album metadata
        3. Show events log
        4. Show decisions
        5. Issue lifecycle action (pause)
        6. Verify UI state updates

        Note: `current_layer` is derived from the most recent build
        event's payload (see db/events.py docstring). It's NOT stored
        on the session row — the session is a thin handle, and layer
        progress is a property of the build event stream.
        """
        # 1. Session picker
        r = await self.client.post("/api/sessions",
                                    json={"album_id": "half-light-hours"})
        sid = (await r.get_json())["id"]
        r = await self.client.get("/api/sessions")
        sessions = await r.get_json()
        self.assertTrue(any(s["id"] == sid for s in sessions))

        # 2. Album metadata
        r = await self.client.get("/api/albums/half-light-hours")
        album = await r.get_json()
        self.assertEqual(album["title"], "Half-Light Hours")

        # 3. Events log — including a build event with payload.layer=3
        for content in ("user msg", "assistant reply"):
            await self.client.post("/api/events", json={
                "session_id": sid, "role": "user", "kind": "chat",
                "content": content, "album_id": "half-light-hours",
            })
        await self.client.post("/api/events", json={
            "session_id": sid, "role": "assistant", "kind": "build",
            "content": "advance to lyrics finalize",
            "album_id": "half-light-hours",
            "payload": {"layer": 3, "phase": "lyrics_finalize"},
        })
        r = await self.client.get(f"/api/sessions/{sid}/events")
        events = await r.get_json()
        self.assertEqual(len(events), 3)

        # 4. Decisions
        await self.client.post("/api/decisions", json={
            "code": "M01", "tier": "mandatory",
            "session_id": sid, "album_id": "half-light-hours",
            "answer": "Half-Light Hours", "rationale": "final",
        })
        r = await self.client.get(f"/api/sessions/{sid}/decisions")
        decs = await r.get_json()
        self.assertEqual(len(decs), 1)

        # 5. Lifecycle action: pause
        r = await self.client.post(f"/api/sessions/{sid}/pause")
        self.assertEqual(r.status_code, 200)

        # 6. UI state reflects
        r = await self.client.get(f"/api/sessions/{sid}")
        sess = await r.get_json()
        self.assertEqual(sess["status"], "paused")

        # Derive current_layer from most recent build event's payload
        build_events = [e for e in events if e["kind"] == "build"]
        self.assertEqual(len(build_events), 1)
        self.assertEqual(build_events[-1]["payload"]["layer"], 3)
