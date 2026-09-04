"""tests/test_ui_smoke.py — Real-browser smoke against a running daemon.

Requires: a healthy daemon at http://127.0.0.1:8765 (auto-spawning watchdog keeps it up).
Pins: the library page renders the album player, all controls present, audio actually plays
on click.

This is a thick test — it launches chromium_headless_shell (bundled with Playwright).
Skip on machines where it isn't installed by setting SKIP_PLAYWRIGHT_TESTS=1.
"""
import os
import socket
import unittest
from pathlib import Path

HERMES_PY = Path(r"C:/Users/lion_/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe")

SKIP = os.environ.get("SKIP_PLAYWRIGHT_TESTS") == "1"


def _chromium_bin():
    """Find a Playwright-bundled chromium_headless_shell."""
    import glob
    cands = sorted(glob.glob(
        r"C:/Users/lion_/AppData/Local/ms-playwright/chromium_headless_shell-*"
        r"/chrome-headless-shell-win64/chrome-headless-shell.exe"
    ))
    return cands[-1] if cands else None


def _daemon_up(url="http://127.0.0.1:8765/api/health"):
    """Return True if daemon responds 2xx within 3s."""
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return 200 <= r.status < 500
    except Exception:
        return False


def _port_open(host="127.0.0.1", port=8765):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        s.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        s.close()


@unittest.skipIf(SKIP, "set SKIP_PLAYWRIGHT_TESTS=1 to skip browser tests")
class TestLibraryUISmoke(unittest.TestCase):
    """Headless chromium loads library.html, asserts player mounted, clicks track 1, asserts playing."""

    @classmethod
    def setUpClass(cls):
        if not _port_open():
            raise unittest.SkipTest("daemon not running on 127.0.0.1:8765; skipping (auto-spawn watchdog handles this in prod)")
        if not _daemon_up():
            raise unittest.SkipTest("daemon /api/health not 2xx; skipping")
        bin_path = _chromium_bin()
        if not bin_path:
            raise unittest.SkipTest("chromium_headless_shell not present in ms-playwright")
        cls.chromium_bin = bin_path

    def test_player_renders_and_audio_plays(self):
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=self.chromium_bin,
                headless=True,
                args=["--no-sandbox", "--disable-gpu"],
            )
            ctx = browser.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            page.goto("http://127.0.0.1:8765/site/library.html",
                      wait_until="networkidle", timeout=20000)
            # Player mounts after JS fetches /api/albums + tracks
            page.wait_for_selector(".lib-player", timeout=10000)

            # DOM-level asserts
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

            # Click track 1, audio must actually play
            page.click(".lib-track[data-track-i='0']")
            page.wait_for_timeout(700)
            src = page.evaluate("(document.querySelector('#lib-audio') || {}).src")
            paused = page.evaluate("(document.querySelector('#lib-audio') || {}).paused")
            cur = page.evaluate("(document.querySelector('#lib-audio') || {}).currentTime || 0")
            self.assertIn("/api/audio/", src or "", f"audio.src not pointing at /api/audio/: {src}")
            self.assertFalse(paused, f"audio.paused should be False after click: {paused}")
            self.assertGreater(cur, 0, f"audio.currentTime should advance after click: {cur}")
            browser.close()


if __name__ == "__main__":
    unittest.main()
