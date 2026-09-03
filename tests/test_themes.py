"""tests/test_themes.py - Day 15 (hour 1) theme switcher tests.

Static + behavior tests for the Omarchy-inspired 4-theme palette:
  - mixtape85 (default)
  - tokyonight
  - catppuccin
  - gruvbox

Run: pytest tests/test_themes.py -v
"""
import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
THEMES_CSS = PROJECT_ROOT / "site" / "themes.css"
THEMES_JS = PROJECT_ROOT / "site" / "themes.js"
STUDIO_HTML = PROJECT_ROOT / "site" / "studio.html"
ALBUMS_HTML = PROJECT_ROOT / "site" / "albums.html"
LIBRARY_HTML = PROJECT_ROOT / "site" / "library.html"


class TestThemesAssets(unittest.TestCase):
    """The theme assets must exist and contain the expected 4 themes."""

    EXPECTED_THEMES = ("mixtape85", "tokyonight", "catppuccin", "gruvbox")

    def test_themes_css_exists_and_nonempty(self):
        self.assertTrue(THEMES_CSS.exists(), f"missing {THEMES_CSS}")
        content = THEMES_CSS.read_text(encoding="utf-8")
        self.assertGreater(len(content), 2000)

    def test_themes_js_exists_and_nonempty(self):
        self.assertTrue(THEMES_JS.exists(), f"missing {THEMES_JS}")
        content = THEMES_JS.read_text(encoding="utf-8")
        self.assertGreater(len(content), 1500)

    def test_all_four_themes_defined_in_css(self):
        """Each theme has its own :root[data-theme="..."] block."""
        content = THEMES_CSS.read_text(encoding="utf-8")
        for theme in self.EXPECTED_THEMES:
            block_pat = re.compile(rf':root\[data-theme="{theme}"\]\s*\{{')
            self.assertIsNotNone(
                block_pat.search(content),
                f"missing :root[data-theme=\"{theme}\"] block in themes.css",
            )

    def test_all_four_themes_in_js_themes_array(self):
        content = THEMES_JS.read_text(encoding="utf-8")
        themematch = re.findall(r'id:\s*"([^"]+)"', content)
        # The THEMES array contains exactly these 4 ids
        for theme in self.EXPECTED_THEMES:
            self.assertIn(theme, themematch,
                          f"theme '{theme}' missing from THEMES array")

    def test_all_themes_define_semantic_vars(self):
        """Each theme's CSS block must override the 7 semantic variables
        that studio.module.css uses: --bg, --bg-soft, --bg-elevated,
        --ink, --ink-soft, --ink-muted, --accent (and at least one of
        --accent-2). Without these, the theme has no visible effect.
        """
        content = THEMES_CSS.read_text(encoding="utf-8")
        # Extract each theme block
        for theme in self.EXPECTED_THEMES:
            m = re.search(
                rf':root\[data-theme="{theme}"\]\s*\{{([^}}]+)\}}',
                content, re.DOTALL,
            )
            self.assertIsNotNone(m, f"theme '{theme}' has no block")
            block = m.group(1)
            for var in ("--bg", "--bg-soft", "--ink", "--accent"):
                self.assertIn(var, block,
                              f"theme '{theme}' missing semantic var {var}")

    def test_theme_persistence_via_localStorage(self):
        """The switcher must persist user choice via localStorage."""
        content = THEMES_JS.read_text(encoding="utf-8")
        self.assertIn("localStorage", content)
        # The storage key
        self.assertIn("studio-theme", content)

    def test_theme_switcher_a11y(self):
        """The dock + swatches must have role= radiogroup/radio + aria-label."""
        content = THEMES_JS.read_text(encoding="utf-8")
        # Look for setAttribute("role", "radiogroup") / setAttribute("role", "radio")
        # (the actual code uses setAttribute with these values).
        self.assertIn('setAttribute("role", "radiogroup")', content)
        self.assertIn('setAttribute("role", "radio")', content)
        self.assertIn('aria-label', content)
        self.assertIn('aria-checked', content)


class TestThemesWiredIntoPages(unittest.TestCase):
    """Each HTML page must load themes.css + themes.js."""

    PAGES = [STUDIO_HTML, ALBUMS_HTML, LIBRARY_HTML]

    def test_pages_load_themes_css(self):
        for page in self.PAGES:
            content = page.read_text(encoding="utf-8")
            self.assertIn('/site/themes.css', content,
                          f"{page.name} missing themes.css link")

    def test_pages_load_themes_js(self):
        for page in self.PAGES:
            content = page.read_text(encoding="utf-8")
            self.assertIn('/site/themes.js', content,
                          f"{page.name} missing themes.js script tag")


class TestThemesNoDollarForEach(unittest.TestCase):
    """Same gotcha #8 guard — themes.js must not use $(...).forEach."""

    def test_themes_js_no_dollar_forEach(self):
        content = THEMES_JS.read_text(encoding="utf-8")
        offenders = re.findall(r"\$\([^)]*\)\.forEach", content)
        self.assertEqual(offenders, [],
                         f"$(...).forEach not allowed: {offenders}")


class TestThemesCSSReducedMotion(unittest.TestCase):
    """The switcher must respect prefers-reduced-motion (a11y)."""

    def test_reduced_motion_query_present(self):
        content = THEMES_CSS.read_text(encoding="utf-8")
        self.assertIn("prefers-reduced-motion", content,
                      "missing @media (prefers-reduced-motion: reduce) block")


if __name__ == "__main__":
    unittest.main()
