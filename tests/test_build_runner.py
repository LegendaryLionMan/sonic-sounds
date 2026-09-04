"""tests/test_build_runner.py - Day 1 Hour 20: build runner animations (10 ideas)."""
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
BR_CSS = PROJECT_ROOT / "site" / "build-runner.css"
STUDIO_HTML = PROJECT_ROOT / "site" / "studio.html"


class TestBuildRunnerAnimations(unittest.TestCase):
    """All 10 Hour-20 ideas."""

    def setUp(self):
        self.content = BR_CSS.read_text(encoding="utf-8")

    def test_br_css_exists(self):
        self.assertTrue(BR_CSS.exists())
        self.assertGreater(len(self.content), 2000)

    def test_idea1_progress_ring_running(self):
        self.assertIn(".build-job.is-running", self.content)
        self.assertIn("@keyframes build-job-spin", self.content)

    def test_idea2_started_flash(self):
        self.assertIn(".build-job.is-queued", self.content)
        self.assertIn("@keyframes build-job-flash", self.content)

    def test_idea3_rotating_indicator(self):
        """Covered by Idea 1's spin animation."""
        self.assertIn("build-job-spin", self.content)

    def test_idea4_done_checkmark(self):
        self.assertIn(".build-job.is-done", self.content)
        self.assertIn('content: "\\2713"', self.content,
                      "✓ glyph as Unicode escape \\2713")

    def test_idea5_failed_x_shake(self):
        self.assertIn(".build-job.is-failed", self.content)
        self.assertIn("build-job-fail-shake", self.content)
        self.assertIn('content: "\\2717"', self.content,
                      "✗ glyph as Unicode escape \\2717")

    def test_idea6_skipped_dash(self):
        self.assertIn(".build-job.is-skipped", self.content)
        self.assertIn("opacity: .4", self.content)
        self.assertIn('content: "\\2014"', self.content,
                      "— glyph as Unicode escape \\2014")

    def test_idea7_cancel_x(self):
        self.assertIn(".build-job.is-cancelled", self.content)
        self.assertIn('content: "\\2715"', self.content,
                      "✕ glyph as Unicode escape \\2715")

    def test_idea8_layer_crossfade(self):
        self.assertIn(".build-layer-transition", self.content)
        self.assertIn(".build-layer-transition .layer.is-current", self.content)
        self.assertIn(".build-layer-transition .layer.is-leaving", self.content)

    def test_idea9_prefers_reduced_motion(self):
        self.assertIn("prefers-reduced-motion", self.content)

    def test_idea10_history_with_timestamps(self):
        self.assertIn(".build-history-timestamp", self.content)
        self.assertIn(".build-history-row.is-recent", self.content)


class TestBuildRunnerWired(unittest.TestCase):
    def test_br_css_in_studio(self):
        content = STUDIO_HTML.read_text(encoding="utf-8")
        self.assertIn("/site/build-runner.css", content)


if __name__ == "__main__":
    unittest.main()
