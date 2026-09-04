"""tests/test_decision_cards.py - Day 1 Hour 7: decision card staggered reveal (10 ideas)."""
import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DECISIONS_CSS = PROJECT_ROOT / "site" / "decisions.css"
STUDIO_HTML = PROJECT_ROOT / "site" / "studio.html"


class TestDecisionCards(unittest.TestCase):
    """All 10 Hour-7 ideas must be implemented as CSS rules."""

    def setUp(self):
        self.content = DECISIONS_CSS.read_text(encoding="utf-8")

    def test_decisions_css_exists_and_nonempty(self):
        self.assertTrue(DECISIONS_CSS.exists())
        self.assertGreater(len(self.content), 2000)

    def test_idea1_slide_in_keyframe(self):
        self.assertIn("@keyframes decision-slide-in", self.content)
        # Keyframe contents: must include translateX start point
        self.assertIn("translateX(80px)", self.content,
                      "decision-slide-in must start from translateX(80px)")
        # Must include overshoot (-8px)
        self.assertIn("translateX(-8px)", self.content,
                      "decision-slide-in must include -8px overshoot")
        # Must end at 0
        self.assertIn("translateX(0)", self.content)

    def test_idea2_spring_bouncy_used(self):
        self.assertRegex(self.content,
                         r"\.decision-card\s*\{[^}]*var\(--spring-bouncy\)",
                         re.DOTALL)

    def test_idea3_duration_token(self):
        self.assertIn("var(--t-decision-enter)", self.content)
        self.assertIn("--t-decision-enter", self.content)

    def test_idea4_hover_lift_and_edit_button(self):
        self.assertRegex(self.content, r"\.decision-card:hover\s*\{[^}]*translateX",
                         re.DOTALL)
        # The .edit-btn reveal uses opacity + transform
        self.assertRegex(self.content,
                         r"\.decision-card\s+\.edit-btn[^}]*opacity:\s*0")
        self.assertRegex(self.content,
                         r"\.decision-card:hover\s+\.edit-btn\s*\{[^}]*opacity:\s*1")

    def test_idea5_expand_keyframe(self):
        self.assertIn("@keyframes decision-expand", self.content)

    def test_idea6_lock_animation(self):
        self.assertIn("@keyframes decision-lock", self.content)
        self.assertIn(".decision-card.is-locking", self.content)

    def test_idea7_color_coded_by_tier(self):
        for tier in ("mandatory", "recommended", "optional"):
            self.assertRegex(self.content,
                             rf'\[data-tier="{tier}"\]')
            self.assertRegex(self.content,
                             rf'\[data-tier="{tier}"\][^}}]*border-left',
                             re.DOTALL)

    def test_idea8_z_index_stacking(self):
        # At least 5 nth-of-type rules with z-index
        z_rules = re.findall(
            r"\.decision-card:nth-of-type\(\d+\)\s*\{\s*z-index", self.content,
        )
        self.assertGreaterEqual(len(z_rules), 5)

    def test_idea9_delete_animation(self):
        self.assertIn("@keyframes decision-delete", self.content)
        self.assertIn(".decision-card.is-deleting", self.content)

    def test_idea10_color_mix_used(self):
        self.assertIn("color-mix(", self.content)
        self.assertIn("color-mix(in srgb", self.content)

    def test_reduced_motion(self):
        self.assertIn("prefers-reduced-motion", self.content)


class TestDecisionCssWired(unittest.TestCase):
    def test_decisions_css_in_pages(self):
        for page in [STUDIO_HTML]:
            content = page.read_text(encoding="utf-8")
            self.assertIn("/site/decisions.css", content,
                          f"{page.name} missing decisions.css link")


if __name__ == "__main__":
    unittest.main()
