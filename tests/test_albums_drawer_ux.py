"""tests/test_albums_drawer_ux.py — Day-1 UX regression tests for the album drawer.

Catches the bug class where the most prominent button in the drawer is a
mutating action that creates state the user doesn't expect.

The user reports:
  "when i click the album tile below album library, it pops up the popup
   to create a session. still cant access the album content..."
Root cause was:
  - '+ Open session' label reads as 'open existing', actually CREATES a session
  - cta-yellow (bright) made it the visually-dominant button
  - user clicked expecting to navigate / see album content

This test asserts:
  1. Button label says 'start new' (or similar — never 'open session' alone)
  2. Button uses a non-primary style class (not cta-yellow)
  3. Button ID exists and is reachable in the drawer
"""
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALBUMS_HTML = PROJECT_ROOT / "site" / "albums.html"


class TestAlbumDrawerUX(unittest.TestCase):
    """Album drawer must not deceive users into creating a session."""

    def test_drawer_button_does_not_say_open_session(self):
        """'+ Open session' reads as 'open existing' but actually creates."""
        html = ALBUMS_HTML.read_text(encoding="utf-8")
        # Allow 'Start new session' or 'Start a session' but NOT 'Open session'
        m_pos = html.find('id="drawer-open-session-btn"')
        self.assertGreater(m_pos, -1, "drawer-open-session-btn not found")
        # Find the closing tag
        m_end = html.find('</button>', m_pos)
        snippet = html[m_pos:m_end]
        # The visible text is whatever's between > and </button>
        text_start = snippet.find('>') + 1
        text = snippet[text_start:].strip()
        self.assertNotIn("open session", text.lower(),
                         f"drawer button text '{text}' reads as 'open existing' — user clicks expecting to navigate, not create")
        self.assertNotEqual(text.strip(), "+ Open session",
                            "drawer button label still says '+ Open session' which misleads")

    def test_drawer_button_uses_secondary_style(self):
        """The start-session button should not be the visual primary CTA."""
        html = ALBUMS_HTML.read_text(encoding="utf-8")
        m_pos = html.find('id="drawer-open-session-btn"')
        m_end = html.find('</button>', m_pos)
        snippet = html[m_pos:m_end]
        # Must NOT have cta-yellow
        self.assertNotIn("cta-yellow", snippet,
                         "drawer-open-session-btn uses cta-yellow — too prominent; demote to cta-secondary")

    def test_drawer_button_text_indicates_create_action(self):
        """Label must make clear it CREATES, not opens."""
        html = ALBUMS_HTML.read_text(encoding="utf-8")
        m_pos = html.find('id="drawer-open-session-btn"')
        m_end = html.find('</button>', m_pos)
        snippet = html[m_pos:m_end]
        text_start = snippet.find('>') + 1
        text = snippet[text_start:].strip().lower()
        create_words = ["start", "new", "create", "begin"]
        has_create_word = any(w in text for w in create_words)
        self.assertTrue(has_create_word,
                        f"drawer button text '{text}' should contain a word like start/new/create/begin to signal 'creates a new session'")


if __name__ == "__main__":
    unittest.main()
