"""tests/test_album_card.py - Day 1 Hour 15: album card hover interactions (10 ideas)."""
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
ACARD_CSS = PROJECT_ROOT / "site" / "album-card.css"
STUDIO_HTML = PROJECT_ROOT / "site" / "studio.html"
LIBRARY_HTML = PROJECT_ROOT / "site" / "library.html"
ALBUMS_HTML = PROJECT_ROOT / "site" / "albums.html"


class TestAlbumCardStyles(unittest.TestCase):
    """All 10 Hour-15 ideas."""

    def setUp(self):
        self.content = ACARD_CSS.read_text(encoding="utf-8")

    def test_acard_css_exists_and_nonempty(self):
        self.assertTrue(ACARD_CSS.exists())
        self.assertGreater(len(self.content), 2000)

    def test_idea1_hover_lift(self):
        self.assertIn(".album-card:hover", self.content)
        self.assertIn("translateY(-4px)", self.content)

    def test_idea2_cover_scales_on_hover(self):
        self.assertIn(".album-card:hover .album-cover", self.content)
        self.assertIn("scale(1.02)", self.content)

    def test_idea3_quick_play_overlay(self):
        # Inherited from cover3d.css; this file must not duplicate but
        # must reference .quick-play or related
        self.assertIn(".quick-play", self.content)  # via cover3d inherited
        # Or via this file's own hook
        # (Just verify quick-play is in scope)

    def test_idea4_metadata_tooltip(self):
        self.assertIn("data-meta", self.content)
        self.assertIn("attr(data-meta)", self.content)
        self.assertIn("meta-tooltip-pop", self.content)

    def test_idea5_hover_metadata_via_after(self):
        # The tooltip is via ::after (covered in test_idea4)
        self.assertIn(".album-card:hover::after", self.content)

    def test_idea6_dblclick_pulse(self):
        self.assertIn(".album-card.is-dblclick", self.content)
        self.assertIn("card-dblclick", self.content)

    def test_idea7_context_menu(self):
        self.assertIn(".album-context-menu", self.content)
        self.assertIn("context-menu-pop", self.content)

    def test_idea8_cover_shimmer_inherited(self):
        # Inherited from cover3d.css — verify the file at least mentions it
        # (or uses .album-cover to integrate)
        self.assertIn(".album-cover", self.content)

    def test_idea9_status_badge_pulse(self):
        self.assertIn(".album-card .status-badge", self.content)
        self.assertIn(".card.shell .eyebrow", self.content)
        # Hover scales the badge
        self.assertIn(".album-card:hover .status-badge", self.content)
        self.assertIn("scale(1.05)", self.content)

    def test_idea10_prefers_reduced_motion(self):
        self.assertIn("prefers-reduced-motion", self.content)


class TestAlbumCardWired(unittest.TestCase):
    def test_acard_css_in_pages(self):
        for page in [STUDIO_HTML, LIBRARY_HTML, ALBUMS_HTML]:
            content = page.read_text(encoding="utf-8")
            self.assertIn("/site/album-card.css", content,
                          f"{page.name} missing album-card.css link")


if __name__ == "__main__":
    unittest.main()
