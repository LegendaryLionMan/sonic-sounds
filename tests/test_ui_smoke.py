"""tests/test_ui_smoke.py — Real-browser smoke against a running daemon.

Default mode: VISIBLE Chrome (CDP on port 9333). The user's main Chrome
profile is cloned to %LOCALAPPDATA%/Temp/sonic-studio-driver so the visible
window looks like theirs but doesn't lock their profile. The smoke then
drives that visible window via Playwright connect_over_cdp.

Headless mode (CI only): set SMOKE_HEADLESS=1 to use bundled
chromium_headless_shell instead. CI never opens an on-screen window.

Pins: the library page renders the album player, all controls present,
audio.src is set on track click (visible mode honors autoplay policy,
so paused=True is expected until the user clicks the page).
"""
import os
import socket
import unittest
from pathlib import Path

HERMES_PY = Path(r"C:/Users/lion_/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe")

SKIP = os.environ.get("SKIP_PLAYWRIGHT_TESTS") == "1"
HEADLESS = os.environ.get("SMOKE_HEADLESS") == "1"
CDP_PORT = 9333


def _port_open(host="127.0.0.1", port=CDP_PORT):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        s.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        s.close()


def _daemon_up(url="http://127.0.0.1:8765/api/health"):
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return 200 <= r.status < 500
    except Exception:
        return False


def _chromium_bin():
    import glob
    cands = sorted(glob.glob(
        r"C:/Users/lion_/AppData/Local/ms-playwright/chromium_headless_shell-*"
        r"/chrome-headless-shell-win64/chrome-headless-shell.exe"
    ))
    return cands[-1] if cands else None


@unittest.skipIf(SKIP, "set SKIP_PLAYWRIGHT_TESTS=1 to skip browser tests")
class TestLibraryUISmoke(unittest.TestCase):
    """Visible Chrome (default) loads library.html, asserts player mounted,
    clicks track 1, asserts audio.src set. Strict playback asserts only run
    in headless mode (no autoplay policy in headless shell)."""

    @classmethod
    def setUpClass(cls):
        if not _port_open(port=8765):
            raise unittest.SkipTest("daemon not running on 127.0.0.1:8765; skipping")
        if not _daemon_up():
            raise unittest.SkipTest("daemon /api/health not 2xx; skipping")
        cls.mode = "headless" if HEADLESS else "visible"
        if cls.mode == "visible":
            # The visible chrome (PID owned by tools/ui_smoke.py or prior session)
            # is expected to already be running with CDP on the port. If not,
            # we skip — the agent / user must launch it.
            if not _port_open(port=CDP_PORT):
                raise unittest.SkipTest(
                    f"visible Chrome CDP not on :{CDP_PORT}; "
                    "run `python tools/ui_smoke.py --visible` first to start it"
                )

    def test_player_renders_and_audio_src_set(self):
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            if self.mode == "visible":
                browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")
                ctx = browser.contexts[0]
                page = None
                for pg in ctx.pages:
                    if pg.url.startswith("http://127.0.0.1:8765"):
                        page = pg
                        break
                if page is None:
                    page = ctx.new_page()
                    page.goto("http://127.0.0.1:8765/site/library.html",
                              wait_until="networkidle", timeout=20000)
            else:
                bin_path = _chromium_bin()
                if not bin_path:
                    raise unittest.SkipTest("chromium_headless_shell not present")
                browser = p.chromium.launch(
                    executable_path=bin_path,
                    headless=True,
                    args=["--no-sandbox", "--disable-gpu"],
                )
                ctx = browser.new_context(viewport={"width": 1280, "height": 900})
                page = ctx.new_page()
                page.goto("http://127.0.0.1:8765/site/library.html",
                          wait_until="networkidle", timeout=20000)

            page.wait_for_selector(".lib-player", timeout=10000)

            # DOM-level asserts (same in both modes)
            self.assertEqual(page.evaluate("document.querySelectorAll('.lib-track').length"),
                             10, "expected 10 track rows")
            self.assertTrue(page.evaluate("!!document.querySelector('#lib-audio')"),
                            "<audio> element missing")
            self.assertTrue(page.evaluate("!!document.querySelector('.lib-seek')"),
                            "seek slider missing")
            self.assertTrue(page.evaluate("!!document.querySelector('.lib-vol')"),
                            "volume slider missing")
            self.assertTrue(page.evaluate("!!document.querySelector('.lib-playpause')"),
                            "play/pause button missing")
            cover_src = page.evaluate("(document.querySelector('.lib-player-cover') || {}).src")
            self.assertIn("/api/albums/half-light-hours/cover", cover_src or "")

            # Click track 1
            page.click(".lib-track[data-track-i='0']")
            page.wait_for_timeout(700)
            src = page.evaluate("(document.querySelector('#lib-audio') || {}).src")
            self.assertIn("/api/audio/", src or "",
                          f"audio.src not pointing at /api/audio/: {src}")

            if self.mode == "headless":
                # Strict: headless shell bypasses autoplay policy
                paused = page.evaluate("(document.querySelector('#lib-audio') || {}).paused")
                cur = page.evaluate("(document.querySelector('#lib-audio') || {}).currentTime || 0")
                self.assertFalse(paused, f"audio.paused should be False in headless: {paused}")
                self.assertGreater(cur, 0, f"audio.currentTime should advance in headless: {cur}")
            else:
                # Visible: Chrome autoplay policy holds; just verify the element is ready
                rs = page.evaluate("(document.querySelector('#lib-audio') || {}).readyState || 0")
                self.assertGreaterEqual(rs, 1, f"audio.readyState should be >= HAVE_METADATA: {rs}")

            browser.close()


if __name__ == "__main__":
    unittest.main()
