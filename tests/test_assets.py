"""tests/test_assets.py - Day 1 Hour 19: asset gallery interactions (10 ideas)."""
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
ASSETS_CSS = PROJECT_ROOT / "site" / "assets.css"
STUDIO_HTML = PROJECT_ROOT / "site" / "studio.html"


class TestAssetsGallery(unittest.TestCase):
    """All 10 Hour-19 ideas."""

    def setUp(self):
        self.content = ASSETS_CSS.read_text(encoding="utf-8")

    def test_assets_css_exists(self):
        self.assertTrue(ASSETS_CSS.exists())
        self.assertGreater(len(self.content), 2000)

    def test_idea1_hover_lift(self):
        self.assertIn(".asset-row:hover", self.content)
        self.assertIn("translateX(4px)", self.content)

    def test_idea2_cover_preview_expand(self):
        self.assertIn('[data-kind="cover"]', self.content)
        self.assertIn('[data-kind="poster"]', self.content)

    def test_idea3_click_to_lightbox(self):
        self.assertIn(".lightbox", self.content)
        self.assertIn("@keyframes lightbox-fade", self.content)
        self.assertIn(".lightbox-img", self.content)
        self.assertIn("lightbox-img-pop", self.content)

    def test_idea4_lightbox_backdrop(self):
        # The .lightbox IS the backdrop
        self.assertIn("backdrop-filter: blur(8px)", self.content)

    def test_idea5_lightbox_keyboard_nav(self):
        self.assertIn(".lightbox-prev", self.content)
        self.assertIn(".lightbox-next", self.content)

    def test_idea6_download_button(self):
        self.assertIn(".download-btn", self.content)
        # Reveals on hover
        self.assertIn(".asset-row:hover .download-btn", self.content)

    def test_idea7_copy_url_button(self):
        self.assertIn(".copy-url-btn", self.content)
        self.assertIn(".is-copied", self.content)

    def test_idea8_kind_filter(self):
        self.assertIn(".asset-filter", self.content)
        self.assertIn(".asset-filter.is-active", self.content)

    def test_idea9_prefers_reduced_motion(self):
        self.assertIn("prefers-reduced-motion", self.content)

    def test_idea10_sort_control(self):
        self.assertIn(".asset-sort-control", self.content)
        self.assertIn(".asset-sort-select", self.content)


class TestAssetsWired(unittest.TestCase):
    def test_assets_css_in_studio(self):
        content = STUDIO_HTML.read_text(encoding="utf-8")
        self.assertIn("/site/assets.css", content)


if __name__ == "__main__":
    unittest.main()
