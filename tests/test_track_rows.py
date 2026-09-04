"""tests/test_track_rows.py - Day 1 Hour 14: track row interactions (10 ideas)."""
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
ROWS_CSS = PROJECT_ROOT / "site" / "track-rows.css"
STUDIO_HTML = PROJECT_ROOT / "site" / "studio.html"


class TestTrackRowStyles(unittest.TestCase):
    """All 10 Hour-14 ideas."""

    def setUp(self):
        self.content = ROWS_CSS.read_text(encoding="utf-8")

    def test_rows_css_exists_and_nonempty(self):
        self.assertTrue(ROWS_CSS.exists())
        self.assertGreater(len(self.content), 2000)

    def test_idea1_hover_reveal(self):
        self.assertIn(".track-row:hover", self.content)
        # The hover changes the bg or transform
        self.assertIn("background: color-mix", self.content)

    def test_idea2_currently_playing_progress(self):
        self.assertIn(".track-row.is-playing", self.content)
        self.assertIn("--track-progress-pct", self.content)
        self.assertIn("track-progress-bar", self.content)

    def test_idea3_timestamp_tooltip(self):
        self.assertIn("data-timestamp", self.content)
        self.assertIn("attr(data-timestamp)", self.content)
        self.assertIn("track-tooltip-pop", self.content)

    def test_idea4_click_to_play(self):
        self.assertIn("cursor: pointer", self.content)
        self.assertIn(".track-row:active", self.content)

    def test_idea5_context_menu(self):
        self.assertIn(".track-context-menu", self.content)
        self.assertIn("context-menu-pop", self.content)

    def test_idea6_cmd_click_multiselect(self):
        self.assertIn(".track-row.is-selected", self.content)
        # The ✓ checkmark appears
        self.assertIn('content: "✓"', self.content)

    def test_idea7_shift_click_range(self):
        self.assertIn(".track-row.is-range-start", self.content)
        self.assertIn(".track-row.is-range-end", self.content)

    def test_idea8_drag_to_reorder(self):
        self.assertIn('draggable="true"', self.content)
        self.assertIn("cursor: grab", self.content)
        self.assertIn(".track-row.is-dragging", self.content)
        self.assertIn(".track-row.is-drag-over", self.content)

    def test_idea9_prefers_reduced_motion(self):
        self.assertIn("prefers-reduced-motion", self.content)

    def test_idea10_keyboard_focus(self):
        self.assertIn(":focus-visible", self.content)
        self.assertIn("outline: 2px solid var(--accent)", self.content)


class TestTrackRowsWired(unittest.TestCase):
    def test_rows_css_in_studio(self):
        content = STUDIO_HTML.read_text(encoding="utf-8")
        self.assertIn("/site/track-rows.css", content)


if __name__ == "__main__":
    unittest.main()
