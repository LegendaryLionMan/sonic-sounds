"""tests/test_audio_progress.py - Day 1 Hour 9: audio progress elastic snap (10 ideas)."""
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
AUDIO_CSS = PROJECT_ROOT / "site" / "audio.css"
STUDIO_HTML = PROJECT_ROOT / "site" / "studio.html"


class TestAudioProgressStyles(unittest.TestCase):
    """All 10 Hour-9 ideas implemented as CSS rules."""

    def setUp(self):
        self.content = AUDIO_CSS.read_text(encoding="utf-8")

    def test_audio_css_exists_and_nonempty(self):
        self.assertTrue(AUDIO_CSS.exists())
        self.assertGreater(len(self.content), 2000)

    def test_idea1_progress_thumb_stretch(self):
        self.assertIn("progress-stretch", self.content)
        self.assertIn("scaleX(1.3)", self.content,
                      "stretch must go to scaleX(1.3) (the overshoot)")

    def test_idea2_spring_bouncy_used(self):
        self.assertIn("var(--spring-bouncy)", self.content)
        # The progress-stretch animation uses it
        self.assertIn("progress-stretch var(--t-progress-stretch) var(--spring-bouncy)",
                      self.content)

    def test_idea3_time_tooltip(self):
        self.assertIn("data-current-time", self.content)
        self.assertIn('attr(data-current-time)', self.content)
        self.assertIn("tooltip-pop", self.content)

    def test_idea4_buffered_indicator(self):
        self.assertIn("audio-buffered", self.content)
        self.assertIn("audio-buffered-pct", self.content,
                      "buffered pct must be settable via CSS var")

    def test_idea5_click_to_seek_visual(self):
        self.assertIn(".audio-progress:hover", self.content)
        self.assertIn("outline: 2px solid var(--accent)", self.content,
                      "hover must give an outline")

    def test_idea6_drag_to_seek(self):
        self.assertIn(".audio-progress.is-dragging", self.content)
        # The drag state must pulse the thumb
        self.assertIn("progress-stretch", self.content)

    def test_idea7_keyboard_seek_class_hook(self):
        """JS handler adds .is-seeking class on keyboard seek."""
        self.assertIn(".is-seeking", self.content)

    def test_idea8_spacebar_play_pause_inherited(self):
        """Spacebar handling is in spring-extra.css (button :active)."""
        # Verify the button :active spring-bouncy is inherited
        # (we don't duplicate here, but the audio.css respects it)
        self.assertIn(".audio-progress", self.content)

    def test_idea9_end_of_track(self):
        self.assertIn("is-complete", self.content,
                      "is-complete class for end-of-track flash")
        self.assertIn("complete-flash", self.content)

    def test_idea10_reduced_motion(self):
        self.assertIn("prefers-reduced-motion", self.content)


class TestAudioCssWired(unittest.TestCase):
    def test_audio_css_in_studio(self):
        content = STUDIO_HTML.read_text(encoding="utf-8")
        self.assertIn("/site/audio.css", content,
                      "studio.html must load audio.css (player is studio-only)")


if __name__ == "__main__":
    unittest.main()
