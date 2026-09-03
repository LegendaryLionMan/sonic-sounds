"""tests/test_theme_carousel.py - Day 1 Hour 4: filterable theme carousel + accent picker tests.

Static + behavior tests for:
  - Filterable theme carousel (opens via trigger, substring filter)
  - Accent color picker (8 curated accents, layered on theme)
  - Per-theme font-family override
"""
import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
THEMES_CSS = PROJECT_ROOT / "site" / "themes.css"
THEMES_JS = PROJECT_ROOT / "site" / "themes.js"


def _find_theme_font(content, theme_id):
    """Find the {display, mono, sans} block for a given theme."""
    # Build pattern as a plain string + compile; avoids Python 3.11
    # backslash issues with raw f-strings in re.compile.
    pattern = r'id:\s*"' + theme_id + r'".*?font:\s*\{([^}]+)\}'
    return re.search(pattern, content, re.DOTALL)


class TestThemeCarousel(unittest.TestCase):
    """Day 1 Hour 4: filterable carousel (Omarchy v4.0 pattern)."""

    def test_carousel_dom_in_themes_js(self):
        content = THEMES_JS.read_text(encoding="utf-8")
        self.assertIn('theme-carousel', content, "missing carousel")
        self.assertIn('theme-carousel-filter', content, "missing filter input")
        self.assertIn('theme-carousel-grid', content, "missing grid")
        self.assertIn('theme-carousel-close', content, "missing close button")
        self.assertIn("window.themeCarousel", content, "missing global API")

    def test_carousel_substring_filter(self):
        """Filter matches by label OR id substring, case-insensitive."""
        content = THEMES_JS.read_text(encoding="utf-8")
        self.assertIn("toLowerCase()", content, "filter must be case-insensitive")
        self.assertIn("t.label.toLowerCase().includes(q)", content)
        self.assertIn("t.id.includes(q)", content)

    def test_carousel_initially_hidden(self):
        """The carousel must be hidden by default; the trigger opens it."""
        content = THEMES_JS.read_text(encoding="utf-8")
        self.assertIn("root.hidden = true", content,
                      "carousel must start hidden to avoid intercepting clicks")

    def test_carousel_keyboard_esc(self):
        content = THEMES_JS.read_text(encoding="utf-8")
        self.assertIn("e.key === \"Escape\"", content,
                      "Esc key must close the carousel")

    def test_carousel_backdrop_click_closes(self):
        content = THEMES_JS.read_text(encoding="utf-8")
        self.assertIn("e.target === root", content,
                      "click on backdrop must close the carousel")

    def test_carousel_css_includes_grid_layout(self):
        content = THEMES_CSS.read_text(encoding="utf-8")
        self.assertIn("theme-carousel-grid", content)
        self.assertIn("grid-template-columns", content,
                      "grid must use auto-fit minmax")

    def test_carousel_css_hidden_rule(self):
        content = THEMES_CSS.read_text(encoding="utf-8")
        # Critical: [hidden] rule must exist so the overlay doesn't
        # intercept clicks when closed.
        self.assertRegex(content, r"\.theme-carousel\[hidden\]\s*\{[^}]*display:\s*none")

    def test_carousel_reduced_motion(self):
        content = THEMES_CSS.read_text(encoding="utf-8")
        self.assertIn("prefers-reduced-motion", content)


class TestAccentPicker(unittest.TestCase):
    """Day 1 Hour 4: theme accent color picker (8 curated accents)."""

    EXPECTED_ACCENTS = ["amber", "cyan", "violet", "rose",
                        "lime", "amber2", "blue", "teal"]

    def test_accent_array_in_themes_js(self):
        content = THEMES_JS.read_text(encoding="utf-8")
        for accent_id in self.EXPECTED_ACCENTS:
            self.assertIn(f'id: "{accent_id}"', content,
                          f"missing accent {accent_id}")

    def test_accent_picker_dom_classes_present(self):
        content = THEMES_JS.read_text(encoding="utf-8")
        self.assertIn("accent-picker", content,
                      "must reference .accent-picker class")
        self.assertIn("accent-swatch", content,
                      "must reference .accent-swatch class")
        self.assertIn("studio:accent-changed", content,
                      "must dispatch accent-changed event")

    def test_accent_picker_toggles_off(self):
        """Clicking the active accent again removes the override."""
        content = THEMES_JS.read_text(encoding="utf-8")
        self.assertIn("currentAccent() === a.id", content)
        self.assertIn("localStorage.removeItem(ACCENT_KEY)", content)

    def test_accent_picker_storage(self):
        content = THEMES_JS.read_text(encoding="utf-8")
        self.assertIn("studio-accent", content)

    def test_accent_swatch_active_state(self):
        content = THEMES_CSS.read_text(encoding="utf-8")
        self.assertIn(".accent-swatch.active", content)

    def test_accent_swatch_uses_color_mix_for_glow(self):
        content = THEMES_CSS.read_text(encoding="utf-8")
        self.assertIn("color-mix", content,
                      "active accent glow should use color-mix")


class TestPerThemeFont(unittest.TestCase):
    """Day 1 Hour 4: per-theme font-family override."""

    EXPECTED_THEMES = ["mixtape85", "tokyonight", "catppuccin", "gruvbox"]

    def test_all_themes_have_font_object(self):
        content = THEMES_JS.read_text(encoding="utf-8")
        for theme_id in self.EXPECTED_THEMES:
            m = _find_theme_font(content, theme_id)
            self.assertIsNotNone(m,
                                 f"theme '{theme_id}' missing font object")

    def test_font_object_includes_all_three_fonts(self):
        content = THEMES_JS.read_text(encoding="utf-8")
        for theme_id in self.EXPECTED_THEMES:
            m = _find_theme_font(content, theme_id)
            block = m.group(1)
            for f in ("display", "mono", "sans"):
                self.assertIn(f, block,
                              f"theme '{theme_id}' font object missing {f}")

    def test_applyFont_sets_css_vars(self):
        content = THEMES_JS.read_text(encoding="utf-8")
        self.assertIn('r.setProperty("--display", font.display)', content)
        self.assertIn('r.setProperty("--mono", font.mono)', content)
        self.assertIn('r.setProperty("--sans", font.sans)', content)

    def test_mixtape85_uses_bebas_neue(self):
        """Mixtape '85 should use Bebas Neue for display (per the brand)."""
        content = THEMES_JS.read_text(encoding="utf-8")
        m = _find_theme_font(content, "mixtape85")
        self.assertIsNotNone(m)
        self.assertIn("Bebas Neue", m.group(1))


class TestThemesJSNoDollarForEach(unittest.TestCase):
    """Same gotcha #8 guard."""

    def test_themes_js_no_dollar_forEach(self):
        content = THEMES_JS.read_text(encoding="utf-8")
        offenders = re.findall(r"\$\([^)]*\)\.forEach", content)
        self.assertEqual(offenders, [], f"got {offenders}")


if __name__ == "__main__":
    unittest.main()
