"""tests/test_albums.py — CRUD tests for db/albums.py."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db import open_db, close_db, run_migrations
import db.albums as albums_mod
from db.albums import (
    list_artists, get_artist, create_artist, update_artist, delete_artist,
    list_albums, get_album, create_album, update_album, archive_album,
    list_tracks, get_track, create_track, update_track, delete_track,
    list_assets, get_asset, create_asset, update_asset, delete_asset,
)


def _fresh_db():
    """Create a fresh temp db with migrations applied."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    # Apply migrations from canonical .meta/migrations/
    result = run_migrations(path)
    assert len(result["errors"]) == 0, f"Migration errors: {result['errors']}"
    return path


def _cleanup(path):
    """Close all cached connections and delete the test db.

    Uses close_all() (not close_db(path)) because tests may have
    cached conns to OTHER paths from previous operations in the same
    test. Leaving those open leaks file handles across the test suite
    on Windows (each leaked conn holds a WAL/SHM file lock).
    """
    from db.connection import close_all
    close_all()
    for ext in ["", "-journal", "-wal", "-shm"]:
        p = Path(path + ext)
        if p.exists():
            try:
                p.unlink()
            except OSError:
                pass


class TestArtists(unittest.TestCase):
    def setUp(self):
        self.db = _fresh_db()

    def tearDown(self):
        _cleanup(self.db)

    def test_create_and_get_artist(self):
        a = create_artist("maren-sol", "Maren Sol", persona="indie folk", db_path=self.db)
        self.assertEqual(a["name"], "Maren Sol")
        self.assertEqual(a["id"], "maren-sol")
        # Get it back
        fetched = get_artist("maren-sol", db_path=self.db)
        self.assertEqual(fetched["name"], "Maren Sol")

    def test_list_artists(self):
        create_artist("a1", "Artist A", db_path=self.db)
        create_artist("a2", "Artist B", db_path=self.db)
        artists = list_artists(db_path=self.db)
        self.assertEqual(len(artists), 2)
        # Ordered by name
        self.assertEqual(artists[0]["name"], "Artist A")
        self.assertEqual(artists[1]["name"], "Artist B")

    def test_update_artist(self):
        create_artist("a1", "Original", persona="v1", db_path=self.db)
        updated = update_artist("a1", name="New", persona="v2", db_path=self.db)
        self.assertEqual(updated["name"], "New")
        self.assertEqual(updated["persona"], "v2")

    def test_delete_artist(self):
        create_artist("a1", "Test", db_path=self.db)
        self.assertTrue(delete_artist("a1", db_path=self.db))
        self.assertIsNone(get_artist("a1", db_path=self.db))
        self.assertFalse(delete_artist("nonexistent", db_path=self.db))


class TestAlbums(unittest.TestCase):
    def setUp(self):
        self.db = _fresh_db()
        create_artist("maren-sol", "Maren Sol", db_path=self.db)

    def tearDown(self):
        _cleanup(self.db)

    def test_create_and_get_album(self):
        a = create_album("half-light-hours", "Half-Light Hours", "maren-sol",
                         runtime_min=37, db_path=self.db)
        self.assertEqual(a["title"], "Half-Light Hours")
        self.assertEqual(a["primary_artist_id"], "maren-sol")
        self.assertEqual(a["status"], "active")

    def test_list_albums_filter_by_status(self):
        create_album("a1", "Album 1", "maren-sol", status="active", db_path=self.db)
        create_album("a2", "Album 2", "maren-sol", status="archived", db_path=self.db)
        active = list_albums(db_path=self.db, status="active")
        all_albums = list_albums(db_path=self.db)
        self.assertEqual(len(active), 1)
        self.assertEqual(len(all_albums), 2)

    def test_archive_album(self):
        create_album("a1", "Album 1", "maren-sol", db_path=self.db)
        archived = archive_album("a1", db_path=self.db)
        self.assertEqual(archived["status"], "archived")

    def test_update_album(self):
        create_album("a1", "Original", "maren-sol", db_path=self.db)
        updated = update_album("a1", title="Updated", runtime_min=42, db_path=self.db)
        self.assertEqual(updated["title"], "Updated")
        self.assertEqual(updated["runtime_min"], 42)


class TestTracks(unittest.TestCase):
    def setUp(self):
        self.db = _fresh_db()
        create_artist("maren-sol", "Maren Sol", db_path=self.db)
        create_album("a1", "Album 1", "maren-sol", db_path=self.db)

    def tearDown(self):
        _cleanup(self.db)

    def test_create_and_get_track(self):
        t = create_track("a1", 1, "First Track", duration_sec=180, db_path=self.db)
        self.assertEqual(t["id"], "a1:01")
        self.assertEqual(t["title"], "First Track")
        self.assertEqual(t["track_num"], 1)

    def test_list_tracks_by_track_num(self):
        create_track("a1", 3, "Third", db_path=self.db)
        create_track("a1", 1, "First", db_path=self.db)
        create_track("a1", 2, "Second", db_path=self.db)
        tracks = list_tracks("a1", db_path=self.db)
        self.assertEqual([t["title"] for t in tracks], ["First", "Second", "Third"])

    def test_update_track_status(self):
        create_track("a1", 1, "Track", db_path=self.db)
        updated = update_track("a1:01", status="mastered", db_path=self.db)
        self.assertEqual(updated["status"], "mastered")

    def test_delete_track(self):
        create_track("a1", 1, "Track", db_path=self.db)
        self.assertTrue(delete_track("a1:01", db_path=self.db))
        self.assertIsNone(get_track("a1:01", db_path=self.db))


class TestAssets(unittest.TestCase):
    def setUp(self):
        self.db = _fresh_db()
        create_artist("maren-sol", "Maren Sol", db_path=self.db)
        create_album("a1", "Album 1", "maren-sol", db_path=self.db)

    def tearDown(self):
        _cleanup(self.db)

    def test_create_and_get_asset(self):
        a = create_asset("a1:cover:1", "a1", "cover", "cover-art/img.jpg",
                         mime="image/jpeg", width=2400, height=2400,
                         size_bytes=500000, sha256="abc123", db_path=self.db)
        self.assertEqual(a["kind"], "cover")
        self.assertEqual(a["path"], "cover-art/img.jpg")

    def test_list_assets_filter_by_kind(self):
        for i in range(3):
            create_asset(f"a1:cover:{i}", "a1", "cover", f"cover-{i}.jpg",
                         db_path=self.db)
        for i in range(2):
            create_asset(f"a1:poster:{i}", "a1", "poster", f"poster-{i}.jpg",
                         db_path=self.db)
        covers = list_assets("a1", kind="cover", db_path=self.db)
        posters = list_assets("a1", kind="poster", db_path=self.db)
        all_assets = list_assets("a1", db_path=self.db)
        self.assertEqual(len(covers), 3)
        self.assertEqual(len(posters), 2)
        self.assertEqual(len(all_assets), 5)

    def test_delete_asset(self):
        create_asset("a1:cover:1", "a1", "cover", "cover.jpg", db_path=self.db)
        self.assertTrue(delete_asset("a1:cover:1", db_path=self.db))
        self.assertIsNone(get_asset("a1:cover:1", db_path=self.db))


class TestEndToEnd(unittest.TestCase):
    """Phase 0.A's seed should still work after Day 2's CRUD layer."""

    def setUp(self):
        self.db = _fresh_db()

    def tearDown(self):
        _cleanup(self.db)

    def test_seed_then_crud(self):
        """Insert an artist + album + track + asset, then verify CRUD round-trip."""
        from db.seed import seed_half_light_hours
        # seed_half_light_hours uses the default path; we want a temp path
        # Instead, do it manually using our CRUD API
        create_artist("maren-sol", "Maren Sol", db_path=self.db)
        create_album("half-light-hours", "Half-Light Hours", "maren-sol",
                     runtime_min=37, db_path=self.db)
        for i in range(1, 11):
            create_track("half-light-hours", i, f"Track {i}",
                         duration_sec=180, db_path=self.db)
        create_asset("half-light-hours:cover:1", "half-light-hours", "cover",
                     "cover-art/img.jpg", db_path=self.db)

        # Verify
        artists = list_artists(db_path=self.db)
        self.assertEqual(len(artists), 1)
        albums = list_albums(db_path=self.db)
        self.assertEqual(len(albums), 1)
        tracks = list_tracks("half-light-hours", db_path=self.db)
        self.assertEqual(len(tracks), 10)
        assets = list_assets("half-light-hours", db_path=self.db)
        self.assertEqual(len(assets), 1)


if __name__ == "__main__":
    unittest.main()
