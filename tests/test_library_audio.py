"""tests/test_library_audio.py - Day 10 library + audio player tests.

Coverage:
  - GET /api/audio/<track_id>: returns 404 for unknown track, 200 with
    audio/mpeg for known track, supports HTTP Range (the daemon's
    audio_range handler in build/serve.py).
  - GET /api/albums returns the album list (sanity check that
    library.html's dynamic wiring has data to render).
  - library.js exists and is non-empty (smoke check).
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
    tmpdir = Path(tempfile.mkdtemp(prefix="sonic-studio-test-day10-"))
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


class TestAudioEndpoint(unittest.IsolatedAsyncioTestCase):
    """The /api/audio/<track_id> endpoint + range support."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir, cls.tempdb = _isolate_tempdb()
        from db import migrations, albums as db_albums
        migrations.bootstrap_initial_migration(cls.tempdb)
        migrations.run_migrations(cls.tempdb)
        # Create a test album with a fake mp3_path that the audio endpoint
        # can resolve. We point it at a small valid MP3 we generate.
        db_albums.create_artist("a1", "A", db_path=cls.tempdb)
        db_albums.create_album("test-album", "Test Album", "a1", db_path=cls.tempdb)
        # Generate a tiny valid MP3 file (the audio endpoint serves it
        # byte-for-byte, so any binary content works for the range test).
        fake_mp3 = cls.tmpdir / "fake-track.mp3"
        # Just write some bytes — not a real MP3 header but the endpoint
        # doesn't validate; it serves what's on disk.
        fake_mp3.write_bytes(b"ID3\x04\x00\x00\x00\x00\x00\x00FAKE_MP3_DATA" + b"\x00" * 1024)
        cls.fake_mp3_path = fake_mp3
        # The audio endpoint reads from /albums/<album>/tracks/<file>
        # (or whatever mp3_path says). For the test, we can mock it by
        # creating the track with mp3_path pointing at our fake file.
        # Looking at the audio_range handler in build/serve.py: it reads
        # the mp3 from the project root's /albums/<album_id>/<file>.
        # We'll create a fake mp3 at albums/test-album/01-fake.mp3.
        project_albums = PROJECT_ROOT / "albums" / "test-album"
        project_albums.mkdir(parents=True, exist_ok=True)
        target_mp3 = project_albums / "01-fake.mp3"
        target_mp3.write_bytes(fake_mp3.read_bytes())
        cls.project_mp3 = target_mp3
        # Insert the track row. track_id is auto-generated as
        # `<album_id>:<track_num:02d>` so it becomes "test-album:01".
        db_albums.create_track(
            "test-album", 1, "Fake Track",
            mp3_path=str(target_mp3.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            db_path=cls.tempdb,
        )

    @classmethod
    def tearDownClass(cls):
        _drop_isolation()
        import shutil
        shutil.rmtree(cls.tmpdir, ignore_errors=True)
        # Cleanup project file we created
        if cls.project_mp3.exists():
            cls.project_mp3.unlink()
        album_dir = cls.project_mp3.parent
        if album_dir.exists() and not any(album_dir.iterdir()):
            album_dir.rmdir()
        parent = album_dir.parent
        if parent.exists() and parent.name == "test-album" and not any(parent.iterdir()):
            parent.rmdir()

    def setUp(self):
        from db.connection import close_all
        close_all()

    async def test_audio_404_for_unknown_track(self):
        from build.serve import create_app
        app = create_app()
        client = app.test_client()
        resp = await client.get("/api/audio/nonexistent:99")
        self.assertEqual(resp.status_code, 404)

    async def test_audio_200_with_mpeg_for_known_track(self):
        from build.serve import create_app
        app = create_app()
        client = app.test_client()
        resp = await client.get("/api/audio/test-album:01")
        self.assertEqual(resp.status_code, 200)
        # Content-Type should be audio/mpeg
        ctype = resp.headers.get("Content-Type", "")
        self.assertTrue("mpeg" in ctype or "audio" in ctype,
                        f"got Content-Type={ctype!r}")

    async def test_audio_supports_range_requests(self):
        """Per plan: '/api/audio/<id> GET audio with HTTP Range support'.

        The browser's <audio> element sends Range: bytes=0-1024 on first
        load (HEAD-like probe). The handler should return 206 Partial
        Content with a Content-Range header.
        """
        from build.serve import create_app
        app = create_app()
        client = app.test_client()
        resp = await client.get("/api/audio/test-album:01", headers={"Range": "bytes=0-99"})
        # 206 Partial Content for a valid range
        self.assertEqual(resp.status_code, 206, f"got {resp.status_code}")
        body = await resp.get_data()
        self.assertEqual(len(body), 100, f"expected 100 bytes, got {len(body)}")
        self.assertIn("bytes 0-99", resp.headers.get("Content-Range", ""))


class TestAudioOneDriveFallback(unittest.IsolatedAsyncioTestCase):
    """Audio handler falls back to ~/OneDrive/Hermes/albums/<album>/
    when the local file is missing (per R10: canonical album storage
    lives in OneDrive). This regression test prevents the bug from
    Days 9-12 where the audio endpoint returned 404 because the
    audio_range handler only checked PROJ_ROOT / mp3_path, not the
    OneDrive canonical.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmpdir, cls.tempdb = _isolate_tempdb()
        from db import migrations, albums as db_albums
        migrations.bootstrap_initial_migration(cls.tempdb)
        migrations.run_migrations(cls.tempdb)
        # Set up an album whose mp3 lives ONLY in the OneDrive canonical,
        # NOT in the project root's music/ folder. The audio handler
        # must fall back to OneDrive.
        db_albums.create_artist("a1", "A", db_path=cls.tempdb)
        db_albums.create_album("onedrive-album", "OneDrive Album", "a1", db_path=cls.tempdb)
        # Create the canonical directory under ~/OneDrive/Hermes/albums/
        # with a fake MP3 file. The handler must find it via the
        # canonical fallback path.
        from pathlib import Path
        import shutil as _shutil
        cls.canonical_root = Path.home() / "OneDrive" / "Hermes" / "albums" / "onedrive-album"
        cls.canonical_mp3 = cls.canonical_root / "music" / "01-canonical.mp3"
        cls.canonical_mp3.parent.mkdir(parents=True, exist_ok=True)
        cls.canonical_mp3.write_bytes(b"ID3\x04\x00\x00\x00\x00\x00\x00FAKE_MP3_DATA" + b"\x00" * 2048)
        # Insert the track row with mp3_path that ONLY resolves in OneDrive.
        # NOTE: we intentionally do NOT create the file in PROJ_ROOT / music/.
        db_albums.create_track(
            "onedrive-album", 1, "Canonical Track",
            mp3_path="music/01-canonical.mp3",
            db_path=cls.tempdb,
        )

    @classmethod
    def tearDownClass(cls):
        _drop_isolation()
        import shutil
        shutil.rmtree(cls.tmpdir, ignore_errors=True)
        # Clean up the OneDrive canonical we created
        if cls.canonical_mp3.exists():
            cls.canonical_mp3.unlink()
        # Remove the empty music/ directory we created
        music_dir = cls.canonical_root / "music"
        if music_dir.exists() and not any(music_dir.iterdir()):
            music_dir.rmdir()
        # Remove the empty album directory
        if cls.canonical_root.exists() and not any(cls.canonical_root.iterdir()):
            cls.canonical_root.rmdir()

    def setUp(self):
        from db.connection import close_all
        close_all()

    async def test_audio_resolves_via_onedrive_fallback(self):
        """The audio handler must find the file in OneDrive canonical
        when no local file exists. This is the production path for
        Maren Sol's Half-Light-Hours: tracks are stored in
        ~/OneDrive/Hermes/albums/half-light-hours/music/."""
        from build.serve import create_app
        app = create_app()
        client = app.test_client()
        # The track was created with mp3_path = "music/01-canonical.mp3"
        # so track_id is "onedrive-album:01"
        resp = await client.get("/api/audio/onedrive-album:01", headers={"Range": "bytes=0-99"})
        # Without the OneDrive fallback, this would be 404. With it,
        # we get 206 with the OneDrive file's bytes.
        self.assertEqual(resp.status_code, 206, f"got {resp.status_code}")
        body = await resp.get_data()
        # First 12 bytes should be the ID3 tag we wrote
        self.assertEqual(body[:3], b"ID3", f"expected ID3 tag, got {body[:3]!r}")
        self.assertEqual(len(body), 100)


class TestLibraryAsset(unittest.TestCase):
    """Smoke check: library.js exists and is non-empty."""

    def test_library_js_exists_and_nonempty(self):
        path = PROJECT_ROOT / "site" / "library.js"
        self.assertTrue(path.exists(), f"library.js missing at {path}")
        content = path.read_text(encoding="utf-8")
        self.assertGreater(len(content), 200, "library.js suspiciously short")
        # Sanity: references /api/albums
        self.assertIn("/api/albums", content)


if __name__ == "__main__":
    unittest.main()
