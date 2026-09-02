"""tests/test_studio_guide.py - Day 13 interactive user guide tests.

Light coverage: validates the guide.js logic doesn't throw on import,
the STEPS array is well-formed, and the localStorage key is consistent.
The DOM behavior is covered by the e2e UX suite (e2e/test_ui_full_ux.py)
which can drive the actual studio page.
"""
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
GUIDE_PATH = PROJECT_ROOT / "site" / "studio.guide.js"


class TestGuideScript(unittest.TestCase):
    """Static checks on the guide script."""

    def test_guide_script_exists_and_nonempty(self):
        self.assertTrue(GUIDE_PATH.exists(), f"missing {GUIDE_PATH}")
        content = GUIDE_PATH.read_text(encoding="utf-8")
        self.assertGreater(len(content), 2000, "guide.js suspiciously short")

    def test_guide_has_4_steps(self):
        """The user manual specifies 4 steps:
        1. invoke-brief
        2. play-track
        3. pause-session
        4. lock-decision
        """
        content = GUIDE_PATH.read_text(encoding="utf-8")
        for step_id in ("invoke-brief", "play-track", "pause-session", "lock-decision"):
            self.assertIn(f"id: '{step_id}'", content,
                          f"missing step: {step_id}")

    def test_guide_uses_localStorage_key(self):
        content = GUIDE_PATH.read_text(encoding="utf-8")
        # The seen-key must be a stable string (used to remember dismissal)
        self.assertIn("studio-guide-seen", content)
        self.assertIn("localStorage", content)

    def test_guide_handles_guide_url_param(self):
        """The guide must respect ?guide=on and ?guide=off URL params."""
        content = GUIDE_PATH.read_text(encoding="utf-8")
        self.assertIn("URLSearchParams", content)
        self.assertIn("'guide'", content)
        self.assertIn("'on'", content)
        self.assertIn("'off'", content)

    def test_guide_handles_show_guide_event(self):
        """The Help button must dispatch 'studio:show-guide' which the
        guide listens for to re-show itself."""
        # studio.js (button handler)
        studio_js = (PROJECT_ROOT / "site" / "studio.js").read_text(encoding="utf-8")
        self.assertIn("studio:show-guide", studio_js)
        # studio.guide.js (listener)
        guide_js = GUIDE_PATH.read_text(encoding="utf-8")
        self.assertIn("studio:show-guide", guide_js)

    def test_help_button_in_studio_html(self):
        studio_html = (PROJECT_ROOT / "site" / "studio.html").read_text(encoding="utf-8")
        self.assertIn('id="help-btn"', studio_html)
        # The button should be labeled "HELP" or include the ❓ emoji
        self.assertTrue(
            "HELP" in studio_html or "❓" in studio_html,
            "help button has no visible label"
        )


class TestGuideRuntime(unittest.TestCase):
    """Verify the guide script doesn't have JS syntax errors via node --check."""

    def test_no_syntax_errors(self):
        """Use node to lint-check the guide. Skip if node isn't installed."""
        node = subprocess.run(["where", "node"], capture_output=True, text=True)
        if node.returncode != 0:
            self.skipTest("node not installed; skipping runtime check")
        r = subprocess.run(
            ["node", "--check", str(GUIDE_PATH)],
            capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0, f"node --check failed: {r.stderr}")


if __name__ == "__main__":
    unittest.main()
