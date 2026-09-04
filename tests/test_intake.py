"""tests/test_intake.py - Day 9 intake + album_briefs tests.

Coverage (~14 tests):
  - db/album_briefs.validate_brief_payload:
    * accepts full M-tier answers
    * rejects empty/missing M-tier questions
    * warns on unknown qids (forward-compat, doesn't fail)
    * rejects non-dict payloads
  - db/album_briefs.upsert_brief / get_brief / list_briefs / delete_brief
  - handlers_intake.submit_intake:
    * JSON path with all M-tier → 200, brief persisted, session opened
    * JSON path with missing M-tier → 200 but validation_errors populated
    * FormData path (intake.html form) → 200, M04_ref1/2/3 collapsed
    * missing primary_artist_id when creating new album → 400
    * no album_id AND no R09_title → 400
    * sonic_dna parsed from M09_sonicDNA JSON
  - handlers_intake.get_brief_endpoint + list_briefs_endpoint
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
    tmpdir = Path(tempfile.mkdtemp(prefix="sonic-studio-test-intake-"))
    tempdb = tmpdir / "test.db"
    os.environ["SONIC_STUDIO_DB_PATH"] = str(tempdb)
    for mod_name in list(sys.modules):
        if mod_name == "db" or mod_name.startswith("db."):
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


# A complete, valid intake payload (9 M-tier + a few R/E for richness)
VALID_QUESTIONS = {
    "M01_concept": "An album about finding calm in the half-light.",
    "M02_scope": "10 tracks, single LP, no features.",
    "M03_genre": "dream-folk",
    "M04_references": ["Maren Sol", "Sufjan Stevens", "Big Thief"],
    "M05_vocal": "Breathy mezzo-soprano, close-mic, intimate.",
    "M06_language": "English",
    "M07_runtime": "42",
    "M08_artist": "Maren Sol",
    "M09_sonicDNA": json.dumps({
        "genre": "dream-folk",
        "tempoProfile": "70-95 BPM",
        "instruments": "acoustic guitar, light piano, brushed drums",
    }),
    "R09_title": "Half-Light Hours",
    "R10_tracklist": "01 Dusk Index, 02 Lease on a Vanishing",
    "R11_motif": "windows",
}


class TestValidateBriefPayload(unittest.TestCase):
    """db/album_briefs.validate_brief_payload — schema validation per Q8."""

    def test_accepts_full_m_tier(self):
        from db.album_briefs import validate_brief_payload
        errs = validate_brief_payload({"questions": VALID_QUESTIONS, "version": "v1"})
        self.assertEqual(errs, [], f"unexpected errors: {errs}")

    def test_rejects_empty_questions_dict(self):
        from db.album_briefs import validate_brief_payload
        errs = validate_brief_payload({"questions": {}, "version": "v1"})
        self.assertTrue(len(errs) >= 1)
        self.assertIn("missing or empty M-tier questions", errs[0])

    def test_rejects_missing_m_tier_keys(self):
        from db.album_briefs import validate_brief_payload
        partial = dict(VALID_QUESTIONS)
        del partial["M01_concept"]
        del partial["M09_sonicDNA"]
        errs = validate_brief_payload({"questions": partial, "version": "v1"})
        self.assertTrue(any("M01_concept" in e and "M09_sonicDNA" in e for e in errs),
                        f"expected both missing keys mentioned, got {errs}")

    def test_rejects_empty_string_answers(self):
        from db.album_briefs import validate_brief_payload
        partial = dict(VALID_QUESTIONS)
        partial["M01_concept"] = "   "  # whitespace only
        errs = validate_brief_payload({"questions": partial, "version": "v1"})
        self.assertTrue(any("M01_concept" in e for e in errs))

    def test_unknown_qids_produce_forward_compat_warning(self):
        from db.album_briefs import validate_brief_payload
        questions = dict(VALID_QUESTIONS)
        questions["R99_future_field"] = "test"
        questions["X01_bleeding_edge"] = "test"
        errs = validate_brief_payload({"questions": questions, "version": "v1"})
        # Unknown qids are warnings, not failures
        self.assertTrue(any("unknown question ids" in e for e in errs))

    def test_non_dict_payload_rejected(self):
        from db.album_briefs import validate_brief_payload
        errs = validate_brief_payload("not a dict")
        self.assertEqual(len(errs), 1)
        self.assertIn("payload must be a dict", errs[0])


class TestAlbumBriefsCRUD(unittest.IsolatedAsyncioTestCase):
    """db/album_briefs.upsert/get/list/delete round-trip."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir, cls.tempdb = _isolate_tempdb()
        from db import migrations, albums as db_albums
        migrations.bootstrap_initial_migration(cls.tempdb)
        migrations.run_migrations(cls.tempdb)
        # album_briefs.album_id FK -> albums.id; create the test albums
        db_albums.create_artist("a1", "Test Artist", db_path=cls.tempdb)
        db_albums.create_album("half-light-hours", "Half-Light Hours", "a1", db_path=cls.tempdb)
        db_albums.create_album("test-album", "Test Album", "a1", db_path=cls.tempdb)
        db_albums.create_album("a1", "A1", "a1", db_path=cls.tempdb)
        db_albums.create_album("a2", "A2", "a1", db_path=cls.tempdb)
        db_albums.create_album("to-delete", "To Delete", "a1", db_path=cls.tempdb)
        db_albums.create_album("dna-test", "DNA Test", "a1", db_path=cls.tempdb)

    @classmethod
    def tearDownClass(cls):
        _drop_isolation()
        import shutil
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def setUp(self):
        """Clear all cached connections before each test.

        Different tests in this class use different cached connections
        from different threads (per-thread cache). Without closing them,
        a previous test's connection can hold a write lock that the
        next test's connection can't acquire (SQLITE_BUSY → 'database
        is locked' on WAL).
        """
        from db.connection import close_all
        close_all()

    async def test_upsert_and_get_round_trip(self):
        from db import album_briefs
        brief = {"questions": VALID_QUESTIONS, "version": "v1"}
        row = album_briefs.upsert_brief("half-light-hours", brief, db_path=self.tempdb)
        self.assertEqual(row["album_id"], "half-light-hours")
        # brief_json is stored, brief is parsed by get_brief into the `brief` key
        self.assertIn("brief", row)
        self.assertEqual(row["brief"]["questions"]["M01_concept"],
                         VALID_QUESTIONS["M01_concept"])
        # Re-fetch
        got = album_briefs.get_brief("half-light-hours", db_path=self.tempdb)
        self.assertIsNotNone(got)
        self.assertEqual(got["album_id"], "half-light-hours")
        self.assertIn("brief_json", got)
        self.assertIn("questions", json.loads(got["brief_json"]))

    async def test_upsert_overwrites_on_conflict(self):
        from db import album_briefs
        brief_v1 = {"questions": dict(VALID_QUESTIONS, M01_concept="v1 concept")}
        brief_v2 = {"questions": dict(VALID_QUESTIONS, M01_concept="v2 concept")}
        album_briefs.upsert_brief("test-album", brief_v1, db_path=self.tempdb)
        album_briefs.upsert_brief("test-album", brief_v2, db_path=self.tempdb)
        got = album_briefs.get_brief("test-album", db_path=self.tempdb)
        # Now should have v2
        questions = json.loads(got["brief_json"])["questions"]
        self.assertEqual(questions["M01_concept"], "v2 concept")

    async def test_list_briefs_returns_all(self):
        from db import album_briefs
        album_briefs.upsert_brief("a1", {"questions": VALID_QUESTIONS}, db_path=self.tempdb)
        album_briefs.upsert_brief("a2", {"questions": VALID_QUESTIONS}, db_path=self.tempdb)
        rows = album_briefs.list_briefs(db_path=self.tempdb)
        self.assertEqual(len(rows), 2)

    async def test_delete_brief_returns_true_for_existing(self):
        from db import album_briefs
        album_briefs.upsert_brief("to-delete", {"questions": VALID_QUESTIONS}, db_path=self.tempdb)
        self.assertTrue(album_briefs.delete_brief("to-delete", db_path=self.tempdb))
        # Second delete returns False
        self.assertFalse(album_briefs.delete_brief("to-delete", db_path=self.tempdb))

    async def test_sonic_dna_persisted_as_json(self):
        from db import album_briefs
        dna = {"genre": "dream-folk", "tempo": "70-95"}
        album_briefs.upsert_brief("dna-test", {"questions": VALID_QUESTIONS},
                                   sonic_dna=dna, db_path=self.tempdb)
        got = album_briefs.get_brief("dna-test", db_path=self.tempdb)
        self.assertEqual(got.get("sonic_dna"), dna)


class TestIntakeHandler(unittest.IsolatedAsyncioTestCase):
    """build/handlers_intake.submit_intake — HTTP endpoint tests."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir, cls.tempdb = _isolate_tempdb()
        from db import migrations, albums as db_albums
        migrations.bootstrap_initial_migration(cls.tempdb)
        migrations.run_migrations(cls.tempdb)
        db_albums.create_artist("maren-sol", "Maren Sol", db_path=cls.tempdb)

    @classmethod
    def tearDownClass(cls):
        _drop_isolation()
        import shutil
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    async def asyncSetUp(self):
        # Close any cached connections from a previous test class —
        # without this, the per-thread connection cache holds a write
        # lock and the next test's BEGIN IMMEDIATE blocks.
        from db.connection import close_all
        close_all()
        from build.serve import create_app
        self.app = create_app()
        self.client = self.app.test_client()

    async def test_submit_json_full_payload_creates_brief_and_session(self):
        payload = {
            "primary_artist_id": "maren-sol",
            "questions": VALID_QUESTIONS,
        }
        resp = await self.client.post("/api/intake/submit", json=payload)
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["album_id"], "half-light-hours")
        self.assertIn("session_id", body)
        # Brief was persisted
        self.assertIsNotNone(body["brief_id"])
        # Validation passed
        self.assertEqual(body["validation_errors"], [])

    async def test_submit_json_with_missing_m_tier_returns_200_with_errors(self):
        payload = {
            "album_id": "half-light-hours",
            "primary_artist_id": "maren-sol",
            "questions": {"M01_concept": "partial"},  # only 1 of 9 M-tier
        }
        resp = await self.client.post("/api/intake/submit", json=payload)
        # We still accept (validation is forgiving on write per design)
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertTrue(len(body["validation_errors"]) >= 1)

    async def test_submit_form_data_creates_brief(self):
        # Simulate intake.html form POST: FormData with name="M01_concept", etc.
        form = {
            "primary_artist_id": "maren-sol",
            **VALID_QUESTIONS,
        }
        # intake.html uses M04_ref1/2/3 (collapsed to M04_references)
        form["M04_ref1"] = "Maren Sol"
        form["M04_ref2"] = "Sufjan Stevens"
        form["M04_ref3"] = "Big Thief"
        del form["M04_references"]
        resp = await self.client.post("/api/intake/submit", form=form)
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertEqual(body["album_id"], "half-light-hours")

    async def test_submit_without_album_id_uses_r09_title_as_slug(self):
        payload = {
            "primary_artist_id": "maren-sol",
            "questions": dict(VALID_QUESTIONS, R09_title="Test Slug Album 2026"),
        }
        resp = await self.client.post("/api/intake/submit", json=payload)
        self.assertEqual(resp.status_code, 200)
        body = await resp.get_json()
        self.assertIn("test-slug-album-2026", body["album_id"])

    async def test_submit_without_album_id_and_no_title_returns_400(self):
        """If album_id is not provided AND the slugify of the title source
        ends up empty, the handler rejects with 400."""
        # Force an unslugifyable title by including only whitespace chars
        # via R09_title — the handler's slugify strips non-alnum, leaving "".
        questions = {"R09_title": "--- !!! ??? ---"}
        payload = {"primary_artist_id": "maren-sol", "questions": questions}
        resp = await self.client.post("/api/intake/submit", json=payload)
        self.assertEqual(resp.status_code, 400)
        body = await resp.get_json()
        self.assertIn("album_id is required OR R09_title", body["error"])

    async def test_submit_without_artist_returns_400(self):
        payload = {
            # No primary_artist_id
            "questions": VALID_QUESTIONS,
        }
        resp = await self.client.post("/api/intake/submit", json=payload)
        self.assertEqual(resp.status_code, 400)
        body = await resp.get_json()
        self.assertIn("primary_artist_id", body["error"])

    async def test_sonic_dna_parsed_from_m09_field(self):
        payload = {
            "primary_artist_id": "maren-sol",
            "questions": VALID_QUESTIONS,
        }
        resp = await self.client.post("/api/intake/submit", json=payload)
        body = await resp.get_json()
        # Brief was persisted with sonic_dna extracted
        # (We can fetch /api/intake/brief/<id> to verify)
        get_resp = await self.client.get(f"/api/intake/brief/{body['album_id']}")
        self.assertEqual(get_resp.status_code, 200)
        brief = await get_resp.get_json()
        dna = json.loads(brief["sonic_dna_json"])
        self.assertEqual(dna["genre"], "dream-folk")

    async def test_get_brief_endpoint_404_for_unknown(self):
        resp = await self.client.get("/api/intake/brief/ghost")
        self.assertEqual(resp.status_code, 404)

    async def test_list_briefs_returns_array(self):
        # Submit one to populate
        await self.client.post("/api/intake/submit", json={
            "primary_artist_id": "maren-sol",
            "questions": VALID_QUESTIONS,
        })
        resp = await self.client.get("/api/intake/briefs")
        self.assertEqual(resp.status_code, 200)
        rows = await resp.get_json()
        self.assertIsInstance(rows, list)
        self.assertGreaterEqual(len(rows), 1)
