"""tests/test_spring_physics.py - Day 1 Hour 5: spring-physics on every interactive surface tests.

Validates that the spring-extra.css file applies:
  - All 3 spring tokens (--spring-bouncy, --spring-soft, --spring-snappy)
  - All 4 duration tokens (--t-press, --t-pop, --t-slide, --t-theme)
  - 10 ideas implemented as CSS rules
  - prefers-reduced-motion media query
  - Visual debug mode hook (data-spring-debug)
"""
import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SPRING_CSS = PROJECT_ROOT / "site" / "spring.css"
SPRING_EXTRA = PROJECT_ROOT / "site" / "spring-extra.css"
STUDIO_HTML = PROJECT_ROOT / "site" / "studio.html"
ALBUMS_HTML = PROJECT_ROOT / "site" / "albums.html"
LIBRARY_HTML = PROJECT_ROOT / "site" / "library.html"


class TestSpringTokens(unittest.TestCase):
    """Tokens must exist in spring.css (the foundation file)."""

    TOKENS = [
        "--spring-bouncy", "--spring-soft", "--spring-snappy",
        "--t-press", "--t-pop", "--t-slide", "--t-theme",
    ]

    def test_spring_css_exists_and_nonempty(self):
        self.assertTrue(SPRING_CSS.exists())
        content = SPRING_CSS.read_text(encoding="utf-8")
        self.assertGreater(len(content), 1000)

    def test_all_3_spring_tokens(self):
        content = SPRING_CSS.read_text(encoding="utf-8")
        for tok in ("--spring-bouncy", "--spring-soft", "--spring-snappy"):
            self.assertIn(tok, content, f"missing spring token {tok}")

    def test_all_4_duration_tokens(self):
        content = SPRING_CSS.read_text(encoding="utf-8")
        for tok in ("--t-press", "--t-pop", "--t-slide", "--t-theme"):
            self.assertIn(tok, content, f"missing duration token {tok}")

    def test_spring_tokens_use_cubic_bezier(self):
        """Tokens should be cubic-bezier approximations of spring curves."""
        content = SPRING_CSS.read_text(encoding="utf-8")
        spring_count = content.count("cubic-bezier")
        self.assertGreaterEqual(spring_count, 3,
                                f"expected ≥3 cubic-bezier springs, got {spring_count}")


class TestSpringExtraCoverage(unittest.TestCase):
    """spring-extra.css must implement all 10 Hour-5 ideas as CSS rules."""

    def setUp(self):
        self.content = SPRING_EXTRA.read_text(encoding="utf-8")

    def test_idea1_pipe_invoke_spring(self):
        """[INVOKE] buttons get spring-bouncy on :active."""
        self.assertIn(".pipe-invoke:active", self.content)
        self.assertIn("var(--spring-bouncy)", self.content)
        # Verify the :active state scales down
        m = re.search(r"\.pipe-invoke:active\s*\{[^}]*scale\(\.?\d+\.?\d*\)", self.content)
        self.assertIsNotNone(m, "[INVOKE] :active must scale")

    def test_idea2_t_play_spring(self):
        """▷ track-play buttons get spring-bouncy."""
        self.assertIn(".t-play:active", self.content)
        self.assertRegex(self.content, r"\.t-play:active\s*\{[^}]*scale\(\.?\d+\.?\d*\)")

    def test_idea3_lifecycle_buttons_spring(self):
        """[⏸ PAUSE / ▶ RESUME / ✓ COMPLETE] get spring-bouncy."""
        self.assertRegex(self.content, r"#btn-pause[^}]*#btn-resume[^}]*#btn-complete", re.DOTALL)
        self.assertRegex(self.content, r"#[^}]*:active\s*\{[^}]*scale\(\.?\d+\.?\d*\)", re.DOTALL)

    def test_idea4_haptic_ripple_120ms(self):
        """120ms scale-down-and-back haptic feedback."""
        self.assertIn("haptic-ripple", self.content)
        # The ripple should use --t-press (120ms)
        self.assertIn("var(--t-press)", self.content)
        # Ripple keyframe should scale up and fade
        m = re.search(
            r"@keyframes\s+haptic-ripple\s*\{[^}]*scale\(\d*\.?\d+\)",
            self.content, re.DOTALL,
        )
        self.assertIsNotNone(m, "haptic-ripple keyframe must include scale")

    def test_idea5_card_hover_overshoot(self):
        """Cards on hover get spring-bouncy with subtle overshoot."""
        self.assertRegex(self.content, r"\.card:hover[^}]*translateY\([^)]+\)", re.DOTALL)
        # Verify spring-bouncy used on hover transition
        self.assertRegex(self.content, r"\.card[^}]*transition[^}]*spring-bouncy", re.DOTALL)

    def test_idea6_toggles_use_spring_snappy(self):
        """Toggles/switches use spring-snappy (no overshoot)."""
        self.assertIn("var(--spring-snappy)", self.content)
        # The [aria-pressed] gets spring-snappy
        self.assertRegex(self.content, r"\[aria-pressed\][^}]*spring-snappy", re.DOTALL)

    def test_idea7_drawer_modal_spring_soft(self):
        """Drawers/modals use spring-soft (gentle settle)."""
        # The #album-drawer and #new-album-modal must use --spring-soft
        drawer = re.search(
            r"#album-drawer[^{]*\{[^}]*spring-soft",
            self.content, re.DOTALL,
        )
        self.assertIsNotNone(drawer, "#album-drawer must use spring-soft")
        modal = re.search(
            r"#new-album-modal[^{]*\{[^}]*spring-soft",
            self.content, re.DOTALL,
        )
        self.assertIsNotNone(modal, "#new-album-modal must use spring-soft")

    def test_idea8_duration_tokens_in_use(self):
        """Duration tokens are referenced at least once each."""
        for tok in ("var(--t-press)", "var(--t-pop)", "var(--t-slide)", "var(--t-theme)"):
            # Note: --t-theme may only be in spring.css, not extra
            if tok == "var(--t-theme)":
                # Check the foundation file too
                f_content = SPRING_CSS.read_text(encoding="utf-8")
                self.assertIn(tok, f_content, f"{tok} not used anywhere")
            else:
                self.assertIn(tok, self.content, f"{tok} not in spring-extra.css")

    def test_idea9_prefers_reduced_motion(self):
        """Reduced motion media query disables springs."""
        self.assertIn("prefers-reduced-motion", self.content)
        # The reduced-motion block must turn off transitions + transforms
        rm_block = re.search(
            r"@media\s+\(prefers-reduced-motion[^{]*\)\s*\{",
            self.content,
        )
        self.assertIsNotNone(rm_block, "missing prefers-reduced-motion media query")
        # Find the closing brace roughly
        start = rm_block.end()
        # Find the end of the block
        depth = 1
        i = start
        while i < len(self.content) and depth > 0:
            if self.content[i] == '{': depth += 1
            elif self.content[i] == '}': depth -= 1
            i += 1
        block_content = self.content[start:i]
        self.assertIn("transition-duration", block_content,
                      "reduced-motion must override transition-duration")
        self.assertIn("animation-duration", block_content,
                      "reduced-motion must override animation-duration")

    def test_idea10_spring_debug_toggle(self):
        """data-spring-debug="1" on <html> enables the visual debug overlay."""
        self.assertIn("data-spring-debug", self.content)
        # The debug mode applies to all interactive elements
        self.assertRegex(
            self.content,
            r":root\[data-spring-debug=\"1\"\]\s+button",
            "debug mode must target buttons",
        )


class TestSpringExtraWired(unittest.TestCase):
    """spring-extra.css must be loaded in all 3 main HTML pages."""

    PAGES = [STUDIO_HTML, ALBUMS_HTML, LIBRARY_HTML]

    def test_pages_load_spring_extra(self):
        for page in self.PAGES:
            content = page.read_text(encoding="utf-8")
            self.assertIn("/site/spring-extra.css", content,
                          f"{page.name} missing spring-extra.css link")


class TestSpringExtraNoDollarForEach(unittest.TestCase):
    """Gotcha #8: no $().forEach in any spring JS (defensive — should be CSS-only)."""

    def test_no_themes_spring_with_forEach(self):
        # spring-extra is CSS-only; this is a sanity check
        for path in [SPRING_CSS, SPRING_EXTRA]:
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("$", content,
                             f"{path.name} should be CSS-only, found $")


if __name__ == "__main__":
    unittest.main()
