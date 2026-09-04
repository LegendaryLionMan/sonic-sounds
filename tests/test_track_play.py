"""tests/test_track_play.py - Day 1 Hour 13: track play button reactive fill (10 ideas)."""
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
PLAY_CSS = PROJECT_ROOT / "site" / "track-play.css"
STUDIO_HTML = PROJECT_ROOT / "site" / "studio.html"


class TestTrackPlayStates(unittest.TestCase):
    """All 10 Hour-13 ideas."""

    def setUp(self):
        self.content = PLAY_CSS.read_text(encoding="utf-8")

    def test_play_css_exists_and_nonempty(self):
        self.assertTrue(PLAY_CSS.exists())
        self.assertGreater(len(self.content), 2000)

    def test_idea1_morph_play_to_pause(self):
        """Click morphs icon — CSS handles the swap via .is-playing."""
        self.assertIn(".t-play.is-playing", self.content)
        self.assertIn(".icon-play", self.content)
        self.assertIn(".icon-pause", self.content)
        # The default shows play, .is-playing shows pause
        self.assertIn(".t-play .icon-pause { display: none; }", self.content)
        self.assertIn(".t-play.is-playing .icon-play", self.content)

    def test_idea2_background_fills_with_accent(self):
        self.assertRegex(self.content,
                         r"\.t-play\.is-playing\s*\{[^}]*background:\s*var\(--accent\)",
                         )

    def test_idea3_click_ripple(self):
        self.assertIn(".t-play.is-rippling", self.content)
        self.assertIn("play-ripple", self.content)
        self.assertIn("--ripple-x", self.content)
        self.assertIn("--ripple-y", self.content)

    def test_idea4_beat_pulse(self):
        self.assertIn("play-pulse", self.content)
        self.assertIn("--t-play-beat", self.content,
                      "JS can override beat duration from BPM")

    def test_idea5_hover_waveform_preview(self):
        self.assertIn(".track-row:hover .t-play", self.content)
        self.assertIn("width: 80px", self.content)

    def test_idea6_loading_spinner(self):
        self.assertIn(".t-play.is-loading", self.content)
        self.assertIn("@keyframes spin", self.content)

    def test_idea7_error_state(self):
        self.assertIn(".t-play.is-error", self.content)
        self.assertIn("error-shake", self.content)
        # Retry symbol
        self.assertIn('content: "↻"', self.content)

    def test_idea8_disabled_state(self):
        self.assertIn(".t-play.is-disabled", self.content)
        self.assertIn("cursor: not-allowed", self.content)

    def test_idea9_active_state(self):
        """Same selector as .is-playing (covered by test_idea2)."""
        # The CSS uses .is-playing as the active state selector
        self.assertIn(".is-playing", self.content)

    def test_idea10_focus_visible_a11y(self):
        self.assertIn(":focus-visible", self.content)
        self.assertIn("outline: 2px solid var(--accent)", self.content)

    def test_reduced_motion(self):
        self.assertIn("prefers-reduced-motion", self.content)


class TestTrackPlayWired(unittest.TestCase):
    def test_play_css_in_studio(self):
        content = STUDIO_HTML.read_text(encoding="utf-8")
        self.assertIn("/site/track-play.css", content)


if __name__ == "__main__":
    unittest.main()
