"""tests/test_modal_drawer.py - Day 1 Hour 8: modal/drawer spring entrance (10 ideas)."""
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
MODALS_CSS = PROJECT_ROOT / "site" / "modals.css"
STUDIO_HTML = PROJECT_ROOT / "site" / "studio.html"
ALBUMS_HTML = PROJECT_ROOT / "site" / "albums.html"
LIBRARY_HTML = PROJECT_ROOT / "site" / "library.html"


class TestModalDrawerStyles(unittest.TestCase):
    """All 10 Hour-8 ideas implemented as CSS rules."""

    def setUp(self):
        self.content = MODALS_CSS.read_text(encoding="utf-8")

    def test_modals_css_exists_and_nonempty(self):
        self.assertTrue(MODALS_CSS.exists())
        self.assertGreater(len(self.content), 2000)

    def test_idea1_modal_translateY_start(self):
        """Modal hidden state has translateY(20px) scale(0.96)."""
        self.assertIn("#new-album-modal[hidden]", self.content)
        self.assertIn("translateY(20px)", self.content)
        self.assertIn("scale(0.96)", self.content)

    def test_idea2_modal_open_state(self):
        """:not([hidden]) flips translateY back to 0."""
        self.assertIn("#new-album-modal:not([hidden])", self.content)
        self.assertIn("translateY(0)", self.content)
        self.assertIn("scale(1)", self.content)

    def test_idea3_backdrop_fade(self):
        """Backdrop has fade-in animation."""
        self.assertIn("backdrop-fade-in", self.content)
        self.assertIn("var(--t-modal-backdrop)", self.content,
                      "backdrop timing must use --t-modal-backdrop token")
        # The backdrop duration must be DIFFERENT from the panel
        # (backdrop is slightly faster per Omarchy parallax UX).
        self.assertIn("--t-modal-backdrop: 280ms", self.content)
        self.assertIn("--t-modal-panel: 320ms", self.content)

    def test_idea4_drawer_translateX_start(self):
        """Drawer hidden state has translateX(20px)."""
        self.assertIn("#album-drawer[hidden]", self.content)
        self.assertIn("translateX(20px)", self.content)

    def test_idea5_drawer_opacity(self):
        """Drawer has opacity transition in [hidden] and :not([hidden])."""
        self.assertIn("#album-drawer[hidden]", self.content)
        self.assertIn("#album-drawer:not([hidden])", self.content)
        self.assertIn("opacity: 1", self.content)

    def test_idea6_close_no_jump(self):
        """Same transition rules apply to both open and close — no jump."""
        # Both [hidden] and :not([hidden]) use the same transition tokens
        self.assertIn("var(--t-modal-panel) var(--spring-soft)",
                      self.content)
        # Critical: the transition is on the BASE selector, not on [hidden]
        self.assertIn("#album-drawer,\n.drawer {", self.content.replace(",\n", ",\n", 1))

    def test_idea7_esc_dismiss_attribute(self):
        """[data-esc-dismiss] is the JS hook for Esc-to-close."""
        self.assertIn("data-esc-dismiss", self.content)

    def test_idea8_focus_visible_styling(self):
        """Focus visible has accent ring inside modal/drawer."""
        self.assertIn(".modal :focus-visible", self.content)
        self.assertIn(".drawer :focus-visible", self.content)
        self.assertIn("outline: 2px solid var(--accent)", self.content)

    def test_idea9_click_outside_backdrop(self):
        """Backdrop element exists for click-outside-to-close."""
        self.assertIn(".modal-backdrop", self.content)
        self.assertIn(".drawer-backdrop", self.content)

    def test_idea10_reduced_motion(self):
        self.assertIn("prefers-reduced-motion", self.content)


class TestModalsCssWired(unittest.TestCase):
    def test_modals_css_in_pages(self):
        for page in [STUDIO_HTML, ALBUMS_HTML, LIBRARY_HTML]:
            content = page.read_text(encoding="utf-8")
            self.assertIn("/site/modals.css", content,
                          f"{page.name} missing modals.css link")


if __name__ == "__main__":
    unittest.main()
