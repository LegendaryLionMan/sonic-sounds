"""tests/test_view_transitions.py - Day 1 Hour 12: View Transitions API (10 ideas)."""
import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
VT_CSS = PROJECT_ROOT / "site" / "transitions.css"
STUDIO_HTML = PROJECT_ROOT / "site" / "studio.html"


class TestViewTransitions(unittest.TestCase):
    """All 10 Hour-12 ideas."""

    def setUp(self):
        self.content = VT_CSS.read_text(encoding="utf-8")

    def test_transitions_css_exists_and_nonempty(self):
        self.assertTrue(VT_CSS.exists())
        self.assertGreater(len(self.content), 2000)

    def test_idea1_view_transition_at_rule(self):
        """@view-transition is the opt-in."""
        self.assertIn("@view-transition", self.content)

    def test_idea2_old_new_animation(self):
        self.assertIn("::view-transition-old(root)", self.content)
        self.assertIn("::view-transition-new(root)", self.content)
        self.assertIn("animation-duration: var(--t-page-morph)", self.content)

    def test_idea3_shared_element_transitions(self):
        self.assertIn("::view-transition-group", self.content)
        self.assertIn("album-cover-*", self.content,
                      "must define a view-transition-name pattern for album covers")

    def test_idea4_navigation_auto(self):
        self.assertIn("navigation: auto", self.content)

    def test_idea5_browser_fallback(self):
        self.assertIn("@supports not", self.content)
        # Fallback uses opacity transition
        self.assertIn("body {", self.content)
        self.assertIn("opacity: 0", self.content)

    def test_idea6_320ms_duration(self):
        self.assertIn("--t-page-morph: 320ms", self.content)

    def test_idea7_reduced_motion(self):
        self.assertIn("prefers-reduced-motion", self.content)

    def test_idea8_uses_view_transition_at_rule(self):
        """Already covered by test_idea1 but also check for pseudo elements."""
        self.assertRegex(self.content,
                         r"::view-transition-(old|new|group)\(")

    def test_idea9_vt_support_detection(self):
        self.assertIn("--vt-supported", self.content)
        self.assertIn("@supports (view-transition-name", self.content)

    def test_idea10_trigger_pattern_documented(self):
        """The CSS file documents how to trigger from JS."""
        # Look for the comment block explaining startViewTransition
        self.assertIn("startViewTransition", self.content,
                      "trigger pattern must be documented for future JS impl")


class TestViewTransitionsWired(unittest.TestCase):
    def test_transitions_css_in_pages(self):
        content = STUDIO_HTML.read_text(encoding="utf-8")
        self.assertIn("/site/transitions.css", content,
                      "studio.html must load transitions.css")


if __name__ == "__main__":
    unittest.main()
