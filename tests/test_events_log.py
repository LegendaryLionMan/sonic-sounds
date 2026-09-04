"""tests/test_events_log.py - Day 1 Hour 18: events log animations (10 ideas)."""
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
EVENTS_CSS = PROJECT_ROOT / "site" / "events.css"
STUDIO_HTML = PROJECT_ROOT / "site" / "studio.html"


class TestEventsLog(unittest.TestCase):
    """All 10 Hour-18 ideas."""

    def setUp(self):
        self.content = EVENTS_CSS.read_text(encoding="utf-8")

    def test_events_css_exists(self):
        self.assertTrue(EVENTS_CSS.exists())
        self.assertGreater(len(self.content), 2000)

    def test_idea1_slide_in_from_top(self):
        self.assertIn("@keyframes event-enter", self.content)
        self.assertIn("translateY(-12px)", self.content,
                      "must enter from the top (negative Y)")

    def test_idea2_spring_bouncy(self):
        self.assertIn("var(--spring-bouncy)", self.content)

    def test_idea3_chat_role_tints(self):
        # Human/user = blue
        self.assertIn('[data-role="user"]', self.content)
        self.assertIn('[data-role="human"]', self.content)
        # Assistant = green
        self.assertIn('[data-role="assistant"]', self.content)

    def test_idea4_build_pulse(self):
        self.assertIn('[data-kind="build"]', self.content)
        self.assertIn("@keyframes event-pulse", self.content)

    def test_idea5_log_monospace(self):
        self.assertIn('[data-kind="log"]', self.content)
        self.assertIn("var(--mono)", self.content)

    def test_idea6_click_expand(self):
        self.assertIn(".event-row.is-expanded", self.content)
        self.assertIn("@keyframes event-expand", self.content)

    def test_idea7_filter_pills(self):
        self.assertIn(".event-filter", self.content)
        self.assertIn(".event-filter.is-active", self.content)

    def test_idea8_autoscroll_indicator(self):
        self.assertIn('data-autoscroll="paused"', self.content)

    def test_idea9_prefers_reduced_motion(self):
        self.assertIn("prefers-reduced-motion", self.content)

    def test_idea10_empty_state(self):
        self.assertIn(".event-empty", self.content)
        self.assertIn("empty-twinkle", self.content)


class TestEventsWired(unittest.TestCase):
    def test_events_css_in_studio(self):
        content = STUDIO_HTML.read_text(encoding="utf-8")
        self.assertIn("/site/events.css", content)


if __name__ == "__main__":
    unittest.main()
