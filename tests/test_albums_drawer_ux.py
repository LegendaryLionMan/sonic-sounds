"""tests/test_albums_drawer_ux.py — Day-1 UX regression tests for the album drawer.

Catches the bug class where the most prominent button in the drawer is a
mutating action that creates state the user doesn't expect.

The user reports:
  "when i click the album tile below album library, it pops up the popup
   to create a session. still cant access the album content..."
Root cause was:
  - '+ Open session' label reads as 'open existing', actually CREATES a session
  - cta-yellow (bright) made it the visually-dominant button
  - user clicked expecting to navigate / see album content

User then said: "i want to right away open the album page and see there all
details, i dont want this side popup!!!"
Fix:
  - Removed the drawer from albums.html entirely
  - Added a dedicated /site/album.html?id=<id> page
  - Card click navigates to album.html
  - This test asserts the drawer is gone and album.html exists.
"""
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALBUMS_HTML = PROJECT_ROOT / "site" / "albums.html"
ALBUMS_JS = PROJECT_ROOT / "site" / "albums.js"
ALBUM_HTML = PROJECT_ROOT / "site" / "album.html"


class TestAlbumDrawerRemoved(unittest.TestCase):
    """Drawer must be gone from albums.html — user wants a dedicated page."""

    def test_albums_html_has_no_drawer_markup(self):
        html = ALBUMS_HTML.read_text(encoding="utf-8")
        self.assertNotIn("album-drawer", html, "album-drawer element still in albums.html — drawer should be removed")
        self.assertNotIn("drawer-backdrop", html, "drawer-backdrop class still in albums.html")
        self.assertNotIn("drawer-open-session-btn", html, "drawer-open-session-btn still in albums.html")

    def test_albums_js_has_no_drawer_code(self):
        js = ALBUMS_JS.read_text(encoding="utf-8")
        self.assertNotIn("openDrawer", js, "openDrawer() function still in albums.js")
        self.assertNotIn("closeDrawer", js, "closeDrawer() function still in albums.js")
        self.assertNotIn("renderDrawer", js, "renderDrawer* functions still in albums.js")
        self.assertNotIn("drawerAlbum", js, "drawerAlbum variable still in albums.js")

    def test_albums_card_click_navigates_to_dedicated_page(self):
        js = ALBUMS_JS.read_text(encoding="utf-8")
        # The card click handler should navigate to /site/album.html?id=
        self.assertIn("/site/album.html?id=", js,
                      "album card click handler should navigate to /site/album.html?id=<id>")

    def test_dedicated_album_page_exists(self):
        self.assertTrue(ALBUM_HTML.exists(),
                        f"site/album.html does not exist — need a dedicated album page")
        html = ALBUM_HTML.read_text(encoding="utf-8")
        # Must have key sections
        for needle in ["/tracks", "/sessions", "/sonic-dna", "/assets", "album-title"]:
            self.assertIn(needle, html, f"album.html missing required section/marker: {needle}")
        # Must read id from query string
        self.assertIn("URLSearchParams", html, "album.html should parse ?id from URL")
        # Must fetch from /api/albums/<id>
        self.assertIn("/api/albums/", html, "album.html should call /api/albums/<id>")
        # Must fetch tracks from /api/albums/<id>/tracks
        self.assertIn("/tracks", html, "album.html should fetch the tracks endpoint")

    def test_album_page_has_play_button_per_track(self):
        html = ALBUM_HTML.read_text(encoding="utf-8")
        self.assertIn("t-play", html, "album.html should have per-track play buttons")
        self.assertIn("/api/audio/", html, "album.html should use /api/audio/<track-id> endpoint")

    def test_album_page_handles_stringified_sonic_dna(self):
        """m09_sonic_dna may arrive as a JSON string; album.html must parse it."""
        html = ALBUM_HTML.read_text(encoding="utf-8")
        self.assertIn("m09_sonic_dna", html)
        self.assertIn("JSON.parse", html, "album.html should JSON.parse sonic DNA if it arrives as a string")


class TestAlbumDrawerUXLegacy(unittest.TestCase):
    """Kept for documentation — original drawer UX bug. Drawer is now removed."""

    def test_album_page_does_not_have_old_drawer_button(self):
        """album.html must NOT have the old yellow '+ Open session' button."""
        if not ALBUM_HTML.exists():
            self.skipTest("album.html not present yet")
        html = ALBUM_HTML.read_text(encoding="utf-8")
        self.assertNotIn('cta-yellow', html, "album.html should not use cta-yellow")
        # Has a session-start button but it must be clearly labeled
        if "open-session-btn" in html or "Start new session" in html:
            self.assertIn("Start new session", html,
                          "session start button must be clearly labeled 'Start new session'")


if __name__ == "__main__":
    unittest.main()
