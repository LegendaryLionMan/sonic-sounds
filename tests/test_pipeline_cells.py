"""tests/test_pipeline_cells.py - Day 1 Hour 16: pipeline cells cascade (10 ideas)."""
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
PL_CSS = PROJECT_ROOT / "site" / "pipeline.css"
STUDIO_HTML = PROJECT_ROOT / "site" / "studio.html"


class TestPipelineCells(unittest.TestCase):
    """All 10 Hour-16 ideas."""

    def setUp(self):
        self.content = PL_CSS.read_text(encoding="utf-8")

    def test_pipeline_css_exists(self):
        self.assertTrue(PL_CSS.exists())
        self.assertGreater(len(self.content), 2000)

    def test_idea1_cascade_delay(self):
        self.assertIn("--t-pipeline-cascade-step", self.content)
        # The cascade-delay is computed from --pipeline-cell-index
        self.assertIn("--cascade-delay", self.content)
        self.assertIn("calc(var(--pipeline-cell-index, 0) *", self.content)

    def test_idea2_80ms_between_cells(self):
        self.assertIn("--t-pipeline-cascade-step: 80ms", self.content)

    def test_idea3_active_cell_glow(self):
        self.assertIn(".pipe-invoke.is-active", self.content)
        self.assertIn("pipeline-pulse", self.content)
        self.assertIn("color-mix(in srgb, var(--accent)", self.content)

    def test_idea4_done_cell_checkmark(self):
        self.assertIn(".pipe-invoke.is-done", self.content)
        self.assertIn("pipeline-done-pop", self.content)
        # The checkmark glyph
        self.assertIn('content: "✓"', self.content)

    def test_idea5_failed_cell(self):
        self.assertIn(".pipe-invoke.is-failed", self.content)
        self.assertIn("pipeline-failed-shake", self.content)
        self.assertIn('content: "✗"', self.content)
        # Red glow
        self.assertIn("ef4444", self.content)

    def test_idea6_pending_dimmed(self):
        self.assertIn(".pipe-invoke.is-pending", self.content)
        self.assertIn("opacity: .35", self.content)

    def test_idea7_spring_bouncy_active(self):
        """The .pipe-invoke base transition uses spring-bouncy."""
        self.assertIn("var(--spring-bouncy)", self.content)

    def test_idea8_pulse_on_click(self):
        self.assertIn(".pipe-invoke:active", self.content)
        self.assertIn("pipeline-click", self.content)

    def test_idea9_hover_phase_tooltip(self):
        self.assertIn("data-phase", self.content)
        self.assertIn("attr(data-phase)", self.content)
        self.assertIn("pipeline-tooltip-pop", self.content)

    def test_idea10_prefers_reduced_motion(self):
        self.assertIn("prefers-reduced-motion", self.content)


class TestPipelineWired(unittest.TestCase):
    def test_pipeline_css_in_studio(self):
        content = STUDIO_HTML.read_text(encoding="utf-8")
        self.assertIn("/site/pipeline.css", content)


if __name__ == "__main__":
    unittest.main()
