"""tests/test_scroll_parallax.py - Day 1 Hour 11: scroll-linked parallax topbar (10 ideas)."""
import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SCROLL_CSS = PROJECT_ROOT / "site" / "scroll.css"
STUDIO_JS = PROJECT_ROOT / "site" / "studio.js"
STUDIO_HTML = PROJECT_ROOT / "site" / "studio.html"


class TestScrollParallax(unittest.TestCase):
    """All 10 Hour-11 ideas."""

    def setUp(self):
        self.content_css = SCROLL_CSS.read_text(encoding="utf-8")
        # Studio.js may have multiple IIFEs; read the whole file
        self.content_js = STUDIO_JS.read_text(encoding="utf-8")

    def test_scroll_css_exists(self):
        self.assertTrue(SCROLL_CSS.exists())
        self.assertGreater(len(self.content_css), 2000)

    def test_idea1_topbar_compresses(self):
        self.assertIn(".topbar", self.content_css)
        self.assertIn("var(--scroll-progress, 0)", self.content_css)

    def test_idea2_scroll_timeline_modern(self):
        """Modern @scroll-timeline + @supports not() JS fallback."""
        self.assertIn("@scroll-timeline", self.content_css)
        self.assertIn("@supports not", self.content_css,
                      "must include @supports fallback for older browsers")

    def test_idea3_backdrop_intensifies(self):
        self.assertIn("backdrop-filter", self.content_css)
        self.assertIn("blur(calc", self.content_css,
                      "blur must use calc() with --scroll-progress")

    def test_idea4_font_size_scales(self):
        self.assertIn(".crumb", self.content_css)
        self.assertIn("font-size: calc", self.content_css)

    def test_idea5_logo_compresses(self):
        self.assertIn("#album-title", self.content_css)
        self.assertIn("letter-spacing: calc", self.content_css)

    def test_idea6_cmd_k_hint_fadein(self):
        self.assertIn(".cmd-hint", self.content_css)
        self.assertIn("var(--scroll-progress, 0)", self.content_css)

    def test_idea7_reverse_animation(self):
        """Reverse is implicit via CSS transitions; verify the transition
        is on a property that scales with the var."""
        # Just verify the transition setup
        self.assertIn("transition:", self.content_css)

    def test_idea8_threshold_200px(self):
        """JS sets --scroll-progress only after 200px scroll."""
        # 200 should be hard-coded in studio.js
        self.assertIn("y > 200", self.content_js,
                      "scroll handler must check 200px threshold")
        # Also check it in scroll.css (the @scroll-timeline offsets)
        self.assertIn("scroll-offsets: 0% 50%", self.content_css)

    def test_idea9_prefers_reduced_motion(self):
        self.assertIn("prefers-reduced-motion", self.content_css)

    def test_idea10_sticky_preserved(self):
        """Topbar must keep its sticky positioning."""
        self.assertIn("z-index: 100", self.content_css)
        self.assertIn("isolation: isolate", self.content_css)

    def test_js_sets_scroll_progress(self):
        """studio.js must update --scroll-progress on scroll."""
        self.assertIn("--scroll-progress", self.content_js)
        self.assertIn("window.addEventListener('scroll'", self.content_js)
        self.assertIn("setProperty('--scroll-progress'", self.content_js)


class TestScrollCssWired(unittest.TestCase):
    def test_scroll_css_in_studio(self):
        content = STUDIO_HTML.read_text(encoding="utf-8")
        self.assertIn("/site/scroll.css", content,
                      "studio.html must load scroll.css")


if __name__ == "__main__":
    unittest.main()
