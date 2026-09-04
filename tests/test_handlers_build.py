"""tests/test_handlers_build.py - HTTP integration tests for /api/build/* (Day 7).

Coverage:
  - POST /api/build/invoke (synchronous + queued)
  - GET /api/build/jobs/<id>
  - POST /api/build/jobs/<id>/cancel
  - GET /api/build/jobs (list with filters)
  - Validation: unknown layer, unknown album, missing fields
  - cancel of running job → 409
  - recover_orphans integration
  - events with session_id=NULL (global build events) round-trip
"""
import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _isolate_tempdb():
    tmpdir = Path(tempfile.mkdtemp(prefix="sonic-studio-test-build-handlers-"))
    tempdb = tmpdir / "test.db"
    os.environ["SONIC_STUDIO_DB_PATH"] = str(tempdb)
    for mod_name in list(sys.modules):
        if (mod_name == "db" or mod_name.startswith("db.")
                or mod_name.startswith("build.")):
            del sys.modules[mod_name]
    return tmpdir, tempdb


def _drop_isolation():
    from db.connection import close_all
    try: close_all()
    except Exception: pass
    for mod_name in list(sys.modules):
        if mod_name == "db" or mod_name.startswith("db."):
            del sys.modules[mod_name]
    os.environ.pop("SONIC_STUDIO_DB_PATH", None)


class TestBuildInvoke(unittest.IsolatedAsyncioTestCase):
    """POST /api/build/invoke — queue + run a build job."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir, cls.tempdb = _isolate_tempdb()
        from db import migrations, albums as db_albums
        migrations.bootstrap_initial_migration(cls.tempdb)
        migrations.run_migrations(cls.tempdb)
        db_albums.create_artist("a1", "Maren Sol", db_path=cls.tempdb)
        db_albums.create_album("half-light-hours", "Half-Light Hours",
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

    async def test_invoke_synchronous_noop_layer_succeeds(self):
        """08_audio_mastering has mmx_action=None — runner returns
        ok=True with synthetic MANUAL.md output."""
        resp = await self.client.post("/api/build/invoke", json={
            "album_id": "half-light-hours",
            "layer_id": "08_audio_mastering",
            "synchronous": True,
        })
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertEqual(body["status"], "done")
        self.assertIn("MANUAL.md", body.get("output_path", ""))
        # A build_started + build_succeeded event was written (session_id=NULL)
        from db.events import list_events_by_album
        events = list_events_by_album("half-light-hours", db_path=self.tempdb)
        phases = [e.get("payload_json") for e in events]
        # Parse payload_json to find build_started/build_succeeded
        import json as _json
        event_phases = []
        for pj in phases:
            if pj:
                try: event_phases.append(_json.loads(pj).get("phase"))
                except Exception: pass
        self.assertIn("build_started", event_phases)
        self.assertIn("build_succeeded", event_phases)

    async def test_invoke_queued_returns_202_with_job_id(self):
        """Asynchronous (synchronous=False) returns 202 with job_id
        and status='todo' — the runner runs separately via a background
        thread (out of scope here; we just verify the queueing path)."""
        resp = await self.client.post("/api/build/invoke", json={
            "album_id": "half-light-hours",
            "layer_id": "08_audio_mastering",
            "synchronous": False,
        })
        self.assertEqual(resp.status_code, 202)
        body = await resp.get_json()
        self.assertIn("job_id", body)
        self.assertEqual(body["status"], "todo")
        self.assertTrue(body["queued"])

    async def test_invoke_unknown_layer_returns_400(self):
        resp = await self.client.post("/api/build/invoke", json={
            "album_id": "half-light-hours",
            "layer_id": "99_does_not_exist",
        })
        self.assertEqual(resp.status_code, 400)
        body = await resp.get_json()
        self.assertIn("layer_id", body["error"])

    async def test_invoke_unknown_album_returns_400(self):
        resp = await self.client.post("/api/build/invoke", json={
            "album_id": "nonexistent-album",
            "layer_id": "08_audio_mastering",
        })
        self.assertEqual(resp.status_code, 400)
        body = await resp.get_json()
        self.assertIn("album_id", body["error"])

    async def test_invoke_missing_fields_returns_400(self):
        resp = await self.client.post("/api/build/invoke", json={"album_id": "half-light-hours"})
        self.assertEqual(resp.status_code, 400)
        body = await resp.get_json()
        self.assertIn("layer_id", body["error"])

    async def test_invoke_with_mock_mmx_image_generate(self):
        """06_cover_art has mmx_action='image.generate'. Mock subprocess.run
        so we don't hit the real mmx CLI."""
        from build import invoke as build_invoke
        mock_proc = type("M", (), {
            "returncode": 0,
            "stdout": "Saved: /tmp/fake/cover.jpg\n",
            "stderr": "",
        })()
        with patch("build.invoke.subprocess.run", return_value=mock_proc):
            resp = await self.client.post("/api/build/invoke", json={
                "album_id": "half-light-hours",
                "layer_id": "06_cover_art",
                "synchronous": True,
            })
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertEqual(body["status"], "done")
        self.assertIn("cover.jpg", body.get("output_path", ""))


class TestBuildJobsRead(unittest.IsolatedAsyncioTestCase):
    """GET /api/build/jobs/<id> + GET /api/build/jobs."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir, cls.tempdb = _isolate_tempdb()
        from db import migrations, albums as db_albums, build_jobs as db_bj
        migrations.bootstrap_initial_migration(cls.tempdb)
        migrations.run_migrations(cls.tempdb)
        db_albums.create_artist("a1", "Maren Sol", db_path=cls.tempdb)
        db_albums.create_album("half-light-hours", "Half-Light Hours",
                                "a1", db_path=cls.tempdb)
        cls.job_id = db_bj.queue_job("half-light-hours", "08_audio_mastering",
                                       db_path=cls.tempdb)["id"]

    @classmethod
    def tearDownClass(cls):
        _drop_isolation()
        import shutil
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    async def asyncSetUp(self):
        from build.serve import create_app
        self.app = create_app()
        self.client = self.app.test_client()

    async def test_get_job_returns_200(self):
        resp = await self.client.get(f"/api/build/jobs/{self.job_id}")
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertEqual(body["id"], self.job_id)
        self.assertEqual(body["album_id"], "half-light-hours")
        self.assertIn("ui_status", body)

    async def test_get_job_not_found_returns_404(self):
        resp = await self.client.get("/api/build/jobs/9999999")
        self.assertEqual(resp.status_code, 404)

    async def test_list_jobs_filters_by_album(self):
        resp = await self.client.get("/api/build/jobs?album_id=half-light-hours")
        self.assertEqual(resp.status_code, 200)
        rows = await resp.get_json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["album_id"], "half-light-hours")
        # Each row has ui_status annotation
        self.assertIn("ui_status", rows[0])

    async def test_list_jobs_filters_by_status(self):
        resp = await self.client.get("/api/build/jobs?status=todo")
        rows = await resp.get_json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "todo")

    async def test_list_jobs_filters_by_layer(self):
        resp = await self.client.get("/api/build/jobs?layer_id=08_audio_mastering")
        rows = await resp.get_json()
        self.assertEqual(len(rows), 1)


class TestBuildCancel(unittest.IsolatedAsyncioTestCase):
    """POST /api/build/jobs/<id>/cancel."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir, cls.tempdb = _isolate_tempdb()
        from db import migrations, albums as db_albums, build_jobs as db_bj
        from db.connection import open_db, close_db
        migrations.bootstrap_initial_migration(cls.tempdb)
        migrations.run_migrations(cls.tempdb)
        db_albums.create_artist("a1", "Maren Sol", db_path=cls.tempdb)
        db_albums.create_album("half-light-hours", "Half-Light Hours",
                                "a1", db_path=cls.tempdb)
        # Clear the seed-populated build_jobs so queue_job creates
        # fresh rows for our test (queue_job is idempotent on
        # (album_id, layer_id), so without this the returned row
        # would have the seed's status='done').
        conn = open_db(cls.tempdb)
        conn.execute("DELETE FROM build_jobs")
        conn.commit()
        close_db()
        cls.todo_job = db_bj.queue_job("half-light-hours", "08_audio_mastering",
                                         db_path=cls.tempdb)["id"]
        done_job = db_bj.queue_job("half-light-hours", "09_metadata_isrc",
                                     db_path=cls.tempdb)["id"]
        db_bj.mark_succeeded(done_job, db_path=cls.tempdb)
        cls.done_job = done_job

    @classmethod
    def tearDownClass(cls):
        _drop_isolation()
        import shutil
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    async def asyncSetUp(self):
        from build.serve import create_app
        self.app = create_app()
        self.client = self.app.test_client()

    async def test_cancel_todo_job_succeeds(self):
        resp = await self.client.post(f"/api/build/jobs/{self.todo_job}/cancel")
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertEqual(body["status"], "blocked")

    async def test_cancel_done_job_returns_409(self):
        resp = await self.client.post(f"/api/build/jobs/{self.done_job}/cancel")
        self.assertEqual(resp.status_code, 409)
        body = await resp.get_json()
        self.assertIn("cannot cancel", body["error"])

    async def test_cancel_unknown_job_returns_404(self):
        resp = await self.client.post("/api/build/jobs/9999999/cancel")
        self.assertEqual(resp.status_code, 404)


class TestGlobalEventsForBuild(unittest.IsolatedAsyncioTestCase):
    """Verify /api/events?album= returns global (session_id=NULL) events
    written by the build runner. This is the foundation the studio's
    [invoke] button relies on to display build output in the chat log."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir, cls.tempdb = _isolate_tempdb()
        from db import migrations, albums as db_albums, build_jobs as db_bj
        migrations.bootstrap_initial_migration(cls.tempdb)
        migrations.run_migrations(cls.tempdb)
        db_albums.create_artist("a1", "Maren Sol", db_path=cls.tempdb)
        db_albums.create_album("half-light-hours", "Half-Light Hours",
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

    async def test_global_build_events_visible_via_album_query(self):
        """After invoking a build, the runner writes 2 events with
        session_id=NULL. GET /api/events?album=<id> should return them."""
        # Invoke a no-op layer (creates 2 events synchronously)
        resp = await self.client.post("/api/build/invoke", json={
            "album_id": "half-light-hours",
            "layer_id": "08_audio_mastering",
            "synchronous": True,
        })
        self.assertEqual(resp.status_code, 200)

        # Now query events via album scope
        resp = await self.client.get("/api/events?album=half-light-hours")
        self.assertEqual(resp.status_code, 200)
        events = await resp.get_json()
        # Should have at least 2 (build_started + build_succeeded)
        self.assertGreaterEqual(len(events), 2)

        # All events must be the album's (no leakage from other albums)
        for e in events:
            self.assertEqual(e["album_id"], "half-light-hours")
            # session_id is NULL (normalized as None by _normalize)
            self.assertIsNone(e.get("session_id"))

    async def test_album_query_rejects_without_filter(self):
        """Without ?album= or ?session= the endpoint should 400 to
        prevent accidental full-table scans."""
        resp = await self.client.get("/api/events")
        self.assertEqual(resp.status_code, 400)
        body = await resp.get_json()
        self.assertIn("session or album", body["error"])


class TestBuildMethods(unittest.TestCase):
    """Unit tests for _ui_status (the helper)."""

    def test_ui_status_mapping(self):
        import importlib
        # Need to load the module without going through serve.py (which
        # pulls in Quart). Directly import handlers_build.
        from build import handlers_build
        self.assertEqual(handlers_build._ui_status("todo"), "queued")
        self.assertEqual(handlers_build._ui_status("running"), "in_progress")
        self.assertEqual(handlers_build._ui_status("done"), "succeeded")
        self.assertEqual(handlers_build._ui_status("failed"), "failed")
        self.assertEqual(handlers_build._ui_status("crashed"), "failed")
        self.assertEqual(handlers_build._ui_status("blocked"), "blocked")
        self.assertEqual(handlers_build._ui_status("unknown"), "unknown")


if __name__ == "__main__":
    unittest.main()
