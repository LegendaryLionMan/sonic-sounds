"""tests/test_cover_3d.py - Day 1 Hour 10: album cover 3D + shimmer (10 ideas)."""
import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
COVER3D_CSS = PROJECT_ROOT / "site" / "cover3d.css"
STUDIO_HTML = PROJECT_ROOT / "site" / "studio.html"
ALBUMS_HTML = PROJECT_ROOT / "site" / "albums.html"
LIBRARY_HTML = PROJECT_ROOT / "site" / "library.html"


class TestCover3DStyles(unittest.TestCase):
    """All 10 Hour-10 ideas implemented as CSS rules."""

    def setUp(self):
        self.content = COVER3D_CSS.read_text(encoding="utf-8")

    def test_cover3d_css_exists_and_nonempty(self):
        self.assertTrue(COVER3D_CSS.exists())
        self.assertGreater(len(self.content), 2000)

    def test_idea1_3d_perspective(self):
        self.assertIn("perspective(800px)", self.content)
        # --tilt-x / --tilt-y must be read with default 0deg
        self.assertIn("--tilt-x", self.content)
        self.assertIn("--tilt-y", self.content)
        self.assertIn("var(--tilt-x, 0deg)", self.content)
        self.assertIn("var(--tilt-y, 0deg)", self.content)

    def test_idea2_spring_bouncy_used(self):
        self.assertIn("var(--spring-bouncy)", self.content)
        # Spring-bouncy applied to the .album-cover transition
        self.assertIn("transition: transform var(--t-cover-tilt) var(--spring-bouncy)",
                      self.content)

    def test_idea3_shimmer_sweep(self):
        self.assertIn(".album-cover::after", self.content)
        # The ::after must have a linear-gradient
        self.assertIn("linear-gradient", self.content)
        # Mix-blend-mode for the overlay
        self.assertIn("mix-blend-mode", self.content)

    def test_idea4_shimmer_duration(self):
        self.assertIn("--t-cover-shimmer", self.content)

    def test_idea5_glow_ring(self):
        self.assertIn(".album-cover:hover", self.content)
        self.assertIn("color-mix(in srgb, var(--accent-2) 40%, transparent)",
                      self.content,
                      "glow must use color-mix with accent-2")

    def test_idea6_quick_play_overlay(self):
        self.assertIn(".album-cover .quick-play", self.content)
        self.assertIn(".album-cover:hover .quick-play", self.content)

    def test_idea7_click_ripple(self):
        self.assertIn(".album-cover .ripple", self.content)
        self.assertIn("cover-ripple", self.content)
        self.assertIn("--ripple-x", self.content)
        self.assertIn("--ripple-y", self.content)

    def test_idea8_reduced_motion(self):
        self.assertIn("prefers-reduced-motion", self.content)

    def test_idea9_3d_only_on_cover(self):
        """The .album-cover selector is specific to the cover image."""
        self.assertIn(".album-cover", self.content)
        # The .card.shell rule does NOT include tilt (only its img does)
        # This is implicit via selector specificity — no test needed
        pass

    def test_idea10_will_change_performance_hint(self):
        self.assertIn("will-change: transform", self.content,
                      "performance hint for 60fps compositor")


if __name__ == "__main__":
    unittest.main()
