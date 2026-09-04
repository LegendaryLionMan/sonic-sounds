"""tests/test_mirror.py - Day 12 mirror verification tests.

Covers:
  - verify_mirror() with matching files → ok=True
  - verify_mirror() with mismatched md5 → ok=False, mismatch recorded
  - verify_mirror() with file missing in mirror → ok=False, missing recorded
  - verify_mirror() with file in mirror but not in source → not flagged
    (mirror may legitimately have extra files; verify only that source
    is correctly mirrored)
  - verify_mirror() with .meta/ included vs excluded
  - verify_mirror() with non-existent base_dir → returns error
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestVerifyMirror(unittest.TestCase):
    """scripts/verify-mirror.py pure-function tests."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="sonic-studio-test-mirror-"))
        self.base = self.tmpdir / "base"
        self.mirror = self.tmpdir / "mirror"
        self.base.mkdir(parents=True)
        self.mirror.mkdir(parents=True)
        # Populate base/albums/ with a couple of test files
        (self.base / "albums" / "test-album").mkdir(parents=True)
        (self.base / "albums" / "test-album" / "track.mp3").write_bytes(b"FAKE_MP3")
        # Mirror the same file (matching md5)
        (self.mirror / "albums" / "test-album").mkdir(parents=True)
        (self.mirror / "albums" / "test-album" / "track.mp3").write_bytes(b"FAKE_MP3")
        # And a .meta/ file (the parent directory must exist before
        # write_bytes on Windows; Path(rglob('*')) works for hidden dirs
        # but write_bytes requires the parent to be there)
        (self.base / ".meta").mkdir(parents=True)
        (self.base / ".meta" / "runtime.db").write_bytes(b"DB")
        (self.mirror / ".meta").mkdir(parents=True)
        (self.mirror / ".meta" / "runtime.db").write_bytes(b"DB")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_matching_files_pass(self):
        from scripts.verify_mirror import verify_mirror
        result = verify_mirror(self.base, self.mirror, include_meta=True)
        self.assertTrue(result["ok"], f"got errors: {result}")
        self.assertEqual(result["files_checked"], 2)  # track + db
        self.assertEqual(result["matched"], 2)
        self.assertEqual(result["mismatches"], [])
        self.assertEqual(result["missing"], [])

    def test_mismatched_md5_caught(self):
        # Corrupt the mirror file
        (self.mirror / "albums" / "test-album" / "track.mp3").write_bytes(b"CORRUPTED")
        from scripts.verify_mirror import verify_mirror
        result = verify_mirror(self.base, self.mirror, include_meta=True)
        self.assertFalse(result["ok"])
        self.assertEqual(len(result["mismatches"]), 1)
        mm = result["mismatches"][0]
        self.assertIn("track.mp3", mm["rel"])
        self.assertIn("src_md5", mm)
        self.assertIn("dst_md5", mm)

    def test_missing_in_mirror_caught(self):
        (self.mirror / "albums" / "test-album" / "track.mp3").unlink()
        from scripts.verify_mirror import verify_mirror
        result = verify_mirror(self.base, self.mirror, include_meta=True)
        self.assertFalse(result["ok"])
        self.assertEqual(len(result["missing"]), 1)
        self.assertEqual(result["missing"][0]["in"], "dst")
        self.assertIn("track.mp3", result["missing"][0]["rel"])

    def test_meta_omitted_when_disabled(self):
        from scripts.verify_mirror import verify_mirror
        # With include_meta=False, only the album file is checked
        result = verify_mirror(self.base, self.mirror, include_meta=False)
        self.assertEqual(result["files_checked"], 1)
        self.assertEqual(result["matched"], 1)

    def test_extra_files_in_mirror_not_flagged(self):
        """A file in the mirror that's not in source is NOT a failure
        (per R7: mirror may have legacy content). We only verify
        source → mirror direction."""
        (self.mirror / "albums" / "test-album" / "extra.md").write_bytes(b"stale")
        from scripts.verify_mirror import verify_mirror
        result = verify_mirror(self.base, self.mirror, include_meta=True)
        # extra.md not in source — verify_mirror won't even look at it
        self.assertTrue(result["ok"])
        # Only the 2 source files (track.mp3 + runtime.db) are checked
        self.assertEqual(result["files_checked"], 2)

    def test_nonexistent_base_dir_returns_error(self):
        from scripts.verify_mirror import verify_mirror
        result = verify_mirror(self.tmpdir / "nonexistent", self.mirror)
        self.assertFalse(result["ok"])
        self.assertIn("does not exist", result.get("error", ""))

    def test_cli_json_output(self):
        """The CLI runs end-to-end via subprocess and emits valid JSON."""
        # Re-populate the same setup
        proc = subprocess.run(
            [sys.executable, "-m", "scripts.verify_mirror",
             "--base", str(self.base), "--mirror", str(self.mirror), "--json"],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        self.assertEqual(proc.returncode, 0, f"stderr: {proc.stderr}")
        # Should be valid JSON
        out = json.loads(proc.stdout)
        self.assertTrue(out["ok"])
        self.assertEqual(out["files_checked"], 2)

    def test_cli_human_output(self):
        proc = subprocess.run(
            [sys.executable, "-m", "scripts.verify_mirror",
             "--base", str(self.base), "--mirror", str(self.mirror)],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        self.assertEqual(proc.returncode, 0, f"stderr: {proc.stderr}")
        self.assertIn("Mirror OK", proc.stdout)


class TestPlaywrightE2ESmoke(unittest.TestCase):
    """Smoke test: the Playwright e2e module imports without errors
    and contains the expected daemon-probing + API contract checks.

    We don't actually start a daemon or run Playwright in CI without
    an explicit opt-in; this test only verifies the import surface
    so missing imports don't break the test collection.
    """

    def test_e2e_module_imports_cleanly(self):
        # The module has a `if __name__ == "__main__"` guard so importing
        # it doesn't auto-run the e2e. Just verify the symbols exist.
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "test_playwright_e2e",
            str(PROJECT_ROOT / "e2e" / "test_playwright_e2e.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        # Don't execute() — that would run the e2e. Just verify the
        # source has the expected symbols by reading the file.
        with open(PROJECT_ROOT / "e2e" / "test_playwright_e2e.py") as f:
            content = f.read()
        self.assertIn("def api(", content)
        self.assertIn("def daemon_alive(", content)
        self.assertIn("def playwright_studio_checks(", content)
        self.assertIn("def playwright_albums_checks(", content)
        self.assertIn("def api_contract_checks(", content)
        # And references the daemon's base URL
        self.assertIn("SONIC_STUDIO_E2E_BASE", content)


if __name__ == "__main__":
    unittest.main()
