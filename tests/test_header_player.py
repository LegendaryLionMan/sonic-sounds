"""tests/test_header_player.py — Persistent header music player regressions.

Locks the behavior so the player doesn't accidentally get removed from pages:
  - All site/*.html pages include header-player.css + header-player.js
  - header-player.js is well-formed JS that mounts on DOMContentLoaded
  - header-player.css declares the .header-player class with fixed positioning
  - Header player has cassette visual (reels + cover art) + transport controls
"""
import os
import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SITE = PROJECT_ROOT / "site"
PAGES = ["albums.html", "studio.html", "library.html", "album.html", "index.html", "intake.html", "dashboard.html"]


class TestHeaderPlayerMountedOnAllPages(unittest.TestCase):
    """Every site page must include the header player assets."""

    def test_header_player_css_exists(self):
        self.assertTrue((SITE / "header-player.css").exists(), "header-player.css missing")

    def test_header_player_js_exists(self):
        self.assertTrue((SITE / "header-player.js").exists(), "header-player.js missing")

    def test_every_page_includes_css_link(self):
        for fname in PAGES:
            html = (SITE / fname).read_text(encoding="utf-8")
            # Must reference header-player.css
            self.assertIn('href="/site/header-player.css"', html,
                          f"{fname} does not include header-player.css link")
            # And the link must be properly closed with > (the prior bug was ">")
            self.assertNotIn('href="/site/header-player.css">>', html,
                             f"{fname} has malformed header-player.css link (extra '>')")
            # The line above must be a complete <link ...> tag, not malformed
            self.assertRegex(html, r'<link rel="stylesheet" href="/site/header-player\.css">',
                             f"{fname} header-player.css link malformed")

    def test_every_page_includes_js_script(self):
        for fname in PAGES:
            html = (SITE / fname).read_text(encoding="utf-8")
            self.assertIn('/site/header-player.js', html,
                          f"{fname} does not include header-player.js script tag")
            # Must be a proper script tag (not malformed)
            self.assertRegex(html, r'<script\s+src="/site/header-player\.js[^"]*"\s*></script>',
                             f"{fname} header-player.js script tag malformed")

    def test_no_malformed_link_tags_anywhere(self):
        """Regression: prior injection bug inserted '>' after an unclosed link."""
        for fname in PAGES:
            html = (SITE / fname).read_text(encoding="utf-8")
            # Find all link tags - each must end with `>`. Use non-greedy + word boundary.
            for m in re.finditer(r'<link\b[^<>]*>', html):
                self.assertTrue(m.group(0).rstrip().endswith('>'),
                                f"{fname} malformed link tag: {m.group(0)!r}")


class TestHeaderPlayerCSS(unittest.TestCase):
    """CSS file declares the player + cassette visual."""

    def test_has_root_header_player_class(self):
        css = (SITE / "header-player.css").read_text(encoding="utf-8")
        self.assertIn(".header-player", css, "CSS missing .header-player class")

    def test_player_is_fixed_positioned(self):
        css = (SITE / "header-player.css").read_text(encoding="utf-8")
        # Find the .header-player { ... } block
        m = re.search(r"\.header-player\s*\{([^}]+)\}", css)
        self.assertIsNotNone(m, ".header-player block not found")
        block = m.group(1)
        self.assertIn("position: fixed", block, "header player must be position: fixed")
        self.assertIn("top: 0", block, "header player must be at top: 0")
        self.assertIn("z-index", block, "header player must have a z-index to overlay content")

    def test_has_cassette_visual(self):
        css = (SITE / "header-player.css").read_text(encoding="utf-8")
        # Must have cassette art + reels
        self.assertIn(".hp-cassette", css)
        self.assertIn(".hp-cassette-art", css)
        self.assertIn(".hp-reels", css)
        self.assertIn(".hp-reel", css)

    def test_reels_have_spin_animation(self):
        css = (SITE / "header-player.css").read_text(encoding="utf-8")
        self.assertIn("@keyframes hp-spin", css, "no @keyframes hp-spin — cassette reels won't spin")
        # And the reel uses the animation
        self.assertIn("animation:", css, "reels must use the spin animation")

    def test_reels_animate_only_when_playing(self):
        css = (SITE / "header-player.css").read_text(encoding="utf-8")
        # The .header-player.is-playing .hp-reel { animation-play-state: running } pattern
        self.assertRegex(css, r"\.header-player\.is-playing\s+\.hp-reel[\s\S]*?animation-play-state:\s*running",
                         "reels must only spin when .is-playing class is present (save CPU)")

    def test_has_transport_controls(self):
        css = (SITE / "header-player.css").read_text(encoding="utf-8")
        for cls in [".hp-btn-play", ".hp-btn-skip", ".hp-seek", ".hp-time", ".hp-vol", ".hp-tracklist-panel"]:
            self.assertIn(cls, css, f"missing control class: {cls}")


class TestHeaderPlayerJS(unittest.TestCase):
    """JS file mounts the player and wires transport."""

    def test_mounts_on_dom_ready(self):
        js = (SITE / "header-player.js").read_text(encoding="utf-8")
        # Either via DOMContentLoaded or if already loaded
        self.assertTrue(
            "DOMContentLoaded" in js or "document.readyState" in js,
            "JS must wait for DOM ready before mounting")

    def test_fetches_albums(self):
        js = (SITE / "header-player.js").read_text(encoding="utf-8")
        self.assertIn("/api/albums", js, "JS must fetch /api/albums to find playable album")

    def test_fetches_tracks(self):
        js = (SITE / "header-player.js").read_text(encoding="utf-8")
        self.assertIn("/tracks", js, "JS must fetch tracks endpoint")

    def test_uses_audio_endpoint(self):
        js = (SITE / "header-player.js").read_text(encoding="utf-8")
        self.assertIn("/api/audio/", js, "JS must use /api/audio/<id> endpoint")

    def test_persists_state_to_localstorage(self):
        js = (SITE / "header-player.js").read_text(encoding="utf-8")
        self.assertIn("localStorage", js, "JS must persist state to localStorage")
        self.assertIn("LS_KEY", js, "JS must define a stable LS_KEY")

    def test_handles_pause_resume(self):
        js = (SITE / "header-player.js").read_text(encoding="utf-8")
        self.assertIn("play", js)
        self.assertIn("pause", js)
        self.assertIn("togglePlay", js, "JS must have a togglePlay function")


if __name__ == "__main__":
    unittest.main()
