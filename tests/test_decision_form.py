"""tests/test_decision_form.py - Day 1 Hour 17: decision drawer slide-in (10 ideas)."""
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
FORM_CSS = PROJECT_ROOT / "site" / "decision-form.css"
STUDIO_HTML = PROJECT_ROOT / "site" / "studio.html"
ALBUMS_HTML = PROJECT_ROOT / "site" / "albums.html"


class TestDecisionFormStyles(unittest.TestCase):
    """All 10 Hour-17 ideas."""

    def setUp(self):
        self.content = FORM_CSS.read_text(encoding="utf-8")

    def test_form_css_exists_and_nonempty(self):
        self.assertTrue(FORM_CSS.exists())
        self.assertGreater(len(self.content), 2000)

    def test_idea1_slide_in_inherited(self):
        """Slide-in from right is covered by modals.css .drawer.
        Verify this file references .drawer for consistency."""
        self.assertIn(".drawer", self.content)

    def test_idea2_backdrop_dim(self):
        self.assertIn(".drawer-backdrop", self.content)
        self.assertIn(".modal-backdrop", self.content)
        self.assertIn("backdrop-filter", self.content)
        self.assertIn("cursor: pointer", self.content)

    def test_idea3_esc_dismiss_hook(self):
        self.assertIn("data-esc-dismiss", self.content)

    def test_idea4_form_fields_focus_ring(self):
        self.assertIn("input:focus-visible", self.content)
        self.assertIn("textarea:focus-visible", self.content)
        self.assertIn("select:focus-visible", self.content)
        self.assertIn("box-shadow: 0 0 0 3px", self.content,
                      "focus ring uses color-mix glow")

    def test_idea5_submit_loading_state(self):
        self.assertIn("btn-submit.is-loading", self.content)
        self.assertIn("btn-spin", self.content)
        self.assertIn('border-top-color: transparent', self.content)

    def test_idea6_cancel_button(self):
        self.assertIn(".btn-cancel", self.content)
        self.assertIn("background: transparent", self.content)

    def test_idea7_validation_errors(self):
        self.assertIn(".field-error", self.content)
        self.assertIn("input.has-error", self.content)
        self.assertIn("error-shake", self.content)
        # The error color
        self.assertIn("#ef4444", self.content)

    def test_idea8_success_animation(self):
        self.assertIn(".form-success", self.content)
        self.assertIn("success-flash", self.content)
        self.assertIn("success-check", self.content)
        # The ✓ symbol
        self.assertIn('content: "✓"', self.content)

    def test_idea9_prefers_reduced_motion(self):
        self.assertIn("prefers-reduced-motion", self.content)

    def test_idea10_form_reset_flash(self):
        self.assertIn(".form.is-resetting", self.content)
        self.assertIn("form-reset-flash", self.content)


class TestDecisionFormWired(unittest.TestCase):
    def test_form_css_in_pages(self):
        for page in [STUDIO_HTML, ALBUMS_HTML]:
            content = page.read_text(encoding="utf-8")
            self.assertIn("/site/decision-form.css", content,
                          f"{page.name} missing decision-form.css")


if __name__ == "__main__":
    unittest.main()
