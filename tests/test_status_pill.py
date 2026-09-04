"""tests/test_status_pill.py - Day 1 Hour 6: status pill state transitions (10 ideas)."""
import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
STATUS_CSS = PROJECT_ROOT / "site" / "status.css"
STUDIO_HTML = PROJECT_ROOT / "site" / "studio.html"
ALBUMS_HTML = PROJECT_ROOT / "site" / "albums.html"
LIBRARY_HTML = PROJECT_ROOT / "site" / "library.html"


class TestStatusPillStyles(unittest.TestCase):
    """All 10 Hour-6 ideas must be implemented as CSS rules."""

    def setUp(self):
        self.content = STATUS_CSS.read_text(encoding="utf-8")

    def test_status_css_exists_and_nonempty(self):
        self.assertTrue(STATUS_CSS.exists())
        self.assertGreater(len(self.content), 2000)

    def test_idea1_color_transition(self):
        """Pill must transition background + border + color across states."""
        self.assertIn(".pill {", self.content)
        self.assertRegex(self.content,
                         r"\.pill\s*\{[^}]*background-color[^}]*var\(--spring-soft\)",
                         re.DOTALL)

    def test_idea2_status_pulse_keyframe(self):
        self.assertIn("@keyframes status-pulse", self.content)
        self.assertIn("scale(1.12)", self.content,
                      "pulse must include the 12% overshoot")
        self.assertIn(".pill.flipped", self.content)

    def test_idea3_active_glow_ring(self):
        self.assertIn(".pill.status-active::before", self.content)
        self.assertIn("glow-rotate", self.content)
        self.assertIn("filter: blur(8px)", self.content)

    def test_idea4_quick_action_hint(self):
        self.assertIn("data-action-hint", self.content)
        self.assertIn('attr(data-action-hint)', self.content,
                      "the hint text is read from the data-attribute")

    def test_idea5_relative_timestamp(self):
        self.assertIn("data-relative", self.content)
        self.assertIn('attr(data-relative)', self.content)

    def test_idea6_count_badge(self):
        self.assertIn(".pill.has-count", self.content)
        self.assertIn("data-count", self.content)

    def test_idea7_color_blind_safe_palette(self):
        self.assertIn("data-cb-safe", self.content)
        # Each state should have a distinct symbol under cb-safe mode
        for sym in ("◐", "✓"):
            self.assertIn(sym, self.content,
                          f"cb-safe mode must include symbol {sym}")

    def test_idea8_count_up_animation(self):
        self.assertIn("count-up", self.content)
        self.assertRegex(self.content,
                         r"@keyframes\s+count-up\s*\{[^}]*scale\(.8\)")

    def test_idea9_emoji_fallback_symbols(self):
        """Each status must have a distinct symbol in CSS pseudo-content."""
        for sym, state in (("●", "status-active"),
                           ("◐", "status-paused"),
                           ("✓", "status-done")):
            pattern = rf"\.{state}::before\s*\{{\s*content:\s*\"{sym}"
            self.assertRegex(self.content, pattern)

    def test_idea10_aria_live_region_styled(self):
        """The aria-live announcer region must be visually hidden."""
        self.assertIn('aria-live="polite"', self.content)
        self.assertIn("sr-only", self.content)
        self.assertRegex(self.content,
                         r"\[aria-live=\"polite\"\]\.sr-only\s*\{",
                         re.DOTALL)

    def test_reduced_motion(self):
        self.assertIn("prefers-reduced-motion", self.content)


class TestStatusCssWired(unittest.TestCase):
    def test_status_css_in_pages(self):
        for page in [STUDIO_HTML, ALBUMS_HTML, LIBRARY_HTML]:
            content = page.read_text(encoding="utf-8")
            self.assertIn("/site/status.css", content,
                          f"{page.name} missing status.css link")


if __name__ == "__main__":
    unittest.main()
