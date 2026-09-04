"""tests/test_library_hover.py - Hour 2: cassette wall animations tests.

Validates:
  - site/library.css exists and contains the drifting-bg animation
  - site/library.js wires mousemove → --tilt-x / --tilt-y CSS vars
  - The card-enter stagger uses nth-child delay rules
  - prefers-reduced-motion media query disables animations
  - No $(...).forEach in library.js (gotcha #8)
"""
import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
LIBRARY_CSS = PROJECT_ROOT / "site" / "library.css"
LIBRARY_JS = PROJECT_ROOT / "site" / "library.js"
LIBRARY_HTML = PROJECT_ROOT / "site" / "library.html"


class TestLibraryAnimationAssets(unittest.TestCase):
    """Static + behavior tests for the Omarchy-inspired cassette wall."""

    def test_library_css_exists_and_nonempty(self):
        self.assertTrue(LIBRARY_CSS.exists())
        content = LIBRARY_CSS.read_text(encoding="utf-8")
        self.assertGreater(len(content), 1500)

    def test_library_js_wires_magnetic_hover(self):
        content = LIBRARY_JS.read_text(encoding="utf-8")
        self.assertIn("mousemove", content)
        self.assertIn("--tilt-x", content)
        self.assertIn("--tilt-y", content)
        self.assertIn("mouseleave", content)

    def test_library_css_has_drifting_background(self):
        """Omarchy's 'deliberate beat, uncorrelated periods' pattern."""
        content = LIBRARY_CSS.read_text(encoding="utf-8")
        self.assertIn("bg-drift-1", content)
        self.assertIn("bg-drift-2", content)
        # Both animations should have unique durations (uncorrelated)
        durations = re.findall(r"(\d+)s\s+ease", content)
        self.assertGreater(len(set(durations)), 1,
                           f"expected uncorrelated durations, got {set(durations)}")

    def test_library_css_has_card_enter_stagger(self):
        """Cards stagger in (per-child animation-delay)."""
        content = LIBRARY_CSS.read_text(encoding="utf-8")
        delays = re.findall(r"animation-delay:\s*([\d.]+)s", content)
        self.assertGreaterEqual(len(delays), 5,
                               f"expected ≥5 stagger delays, got {delays}")

    def test_library_css_respects_prefers_reduced_motion(self):
        content = LIBRARY_CSS.read_text(encoding="utf-8")
        self.assertIn("prefers-reduced-motion", content)
        self.assertIn("reduce", content)

    def test_library_js_no_dollar_forEach(self):
        content = LIBRARY_JS.read_text(encoding="utf-8")
        offenders = re.findall(r"\$\([^)]*\)\.forEach", content)
        self.assertEqual(offenders, [], f"got {offenders}")

    def test_library_uses_querySelectorAll_for_each_iteration(self):
        """Per gotcha #8: multi-element iteration must use querySelectorAll."""
        content = LIBRARY_JS.read_text(encoding="utf-8")
        self.assertIn("querySelectorAll", content)


class TestLibraryWiredIntoPage(unittest.TestCase):
    def test_library_html_loads_library_css(self):
        content = LIBRARY_HTML.read_text(encoding="utf-8")
        self.assertIn("/site/library.css", content)


if __name__ == "__main__":
    unittest.main()
