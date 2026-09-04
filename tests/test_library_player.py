"""tests/test_library_player.py - Day 2 Hour X: top-level library page album player."""
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
BASE = "http://127.0.0.1:8765"


class TestLibraryPlayerMarkup(unittest.TestCase):
    """library.html exposes the player mount slot and ships the player files."""

    def test_library_html_has_mount_slot(self):
        with urllib.request.urlopen(f"{BASE}/site/library.html", timeout=5) as r:
            html = r.read().decode("utf-8")
        self.assertIn('id="library-player-mount"', html,
                      "library.html must include a #library-player-mount slot")

    def test_library_html_links_player_js(self):
        with urllib.request.urlopen(f"{BASE}/site/library.html", timeout=5) as r:
            html = r.read().decode("utf-8")
        self.assertIn("/site/library-player.js", html,
                      "library.html must include the player JS")

    def test_library_html_links_player_css(self):
        with urllib.request.urlopen(f"{BASE}/site/library.html", timeout=5) as r:
            html = r.read().decode("utf-8")
        self.assertIn("/site/library-player.css", html,
                      "library.html must link the player CSS")

    def test_mount_slot_in_main_between_hero_and_grid(self):
        """The mount must sit above .shell-grid (so player is visible without scrolling)."""
        with urllib.request.urlopen(f"{BASE}/site/library.html", timeout=5) as r:
            html = r.read().decode("utf-8")
        i_mount = html.find("library-player-mount")
        i_grid = html.find("shell-grid")
        self.assertGreater(i_mount, 0)
        self.assertGreater(i_grid, 0)
        self.assertLess(i_mount, i_grid,
                        "Player mount must render BEFORE the cassette wall")


class TestLibraryPlayerAssets(unittest.TestCase):
    """JS and CSS files exist and serve, contain key selectors."""

    def test_player_js_served(self):
        with urllib.request.urlopen(f"{BASE}/site/library-player.js", timeout=5) as r:
            js = r.read().decode("utf-8")
        self.assertIn("lib-player", js)
        self.assertIn("/api/albums", js)
        self.assertIn("/api/audio/", js)
        # Audio element present in template
        self.assertIn("audio", js.lower())
        # Standard controls
        for ctrl in ["playpause", "prev", "next", "seek", "vol"]:
            self.assertIn(ctrl, js, f"Player JS missing control: {ctrl}")

    def test_player_css_served(self):
        with urllib.request.urlopen(f"{BASE}/site/library-player.css", timeout=5) as r:
            css = r.read().decode("utf-8")
        self.assertIn(".lib-player", css)
        self.assertIn(".lib-tracklist", css)
        self.assertIn(".lib-progress", css)
        self.assertIn(".lib-playpause", css)

    def test_player_js_uses_existing_audio_paths(self):
        """Audio path matches what /api/audio/<track-id> actually serves."""
        with urllib.request.urlopen(f"{BASE}/site/library-player.js", timeout=5) as r:
            js = r.read().decode("utf-8")
        self.assertIn("/api/audio/${", js,
                      "Player must use the /api/audio/<id> route pattern")


class TestApiRequiredByPlayer(unittest.TestCase):
    """The player fetches these endpoints — they must return real data with Maren Sol re-seeded."""

    def test_albums_returns_at_least_one(self):
        with urllib.request.urlopen(f"{BASE}/api/albums", timeout=5) as r:
            albums = []
            import json
            data = r.read()
            try:
                parsed = json.loads(data)
                if isinstance(parsed, list):
                    albums = parsed
                elif isinstance(parsed, dict) and "items" in parsed:
                    albums = parsed["items"]
            except Exception:
                pass
        self.assertGreater(len(albums), 0, "/api/albums must return at least 1 album for the player")

    def test_tracks_endpoint_serves_tracks_for_at_least_one_album(self):
        """Find any album, verify it has tracks."""
        import json
        with urllib.request.urlopen(f"{BASE}/api/albums", timeout=5) as r:
            parsed = json.loads(r.read())
        albums = parsed if isinstance(parsed, list) else parsed.get("items", [])
        self.assertTrue(albums, "no albums")
        album_id = albums[0]["id"]
        with urllib.request.urlopen(
            f"{BASE}/api/albums/{album_id}/tracks", timeout=5
        ) as r:
            tracks = json.loads(r.read())
        self.assertGreater(len(tracks), 0, "first album has no tracks")

    def test_audio_endpoint_supports_range_request(self):
        """The player's seek slider will fire range requests — they must return 206."""
        import json
        with urllib.request.urlopen(f"{BASE}/api/albums", timeout=5) as r:
            parsed = json.loads(r.read())
        albums = parsed if isinstance(parsed, list) else parsed.get("items", [])
        album_id = albums[0]["id"]
        with urllib.request.urlopen(
            f"{BASE}/api/albums/{album_id}/tracks", timeout=5
        ) as r:
            tracks = json.loads(r.read())
        track_id = tracks[0]["id"]
        req = urllib.request.Request(
            f"{BASE}/api/audio/{track_id}",
            headers={"Range": "bytes=0-1"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            self.assertEqual(
                r.status, 206,
                "Audio range request must return 206 Partial Content for seek to work"
            )


if __name__ == "__main__":
    unittest.main()
