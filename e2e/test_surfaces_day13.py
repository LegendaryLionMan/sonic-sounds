"""e2e/test_surfaces_day13.py — Day 13-14 surface coverage (e2e additions).

Adds four new test suites to the album-studio e2e pyramid:
  - suite_cover_art        : /api/albums/<id>/cover streams JPEG
  - suite_audio_streaming  : /api/audio/<track> 206 + ID3 bytes
  - suite_guide_overlay    : studio.html loads studio.guide.js + Help
  - suite_track_count      : /api/albums returns track_count

Why this file is separate from test_ui_full_ux.py: it covers the
Day 13-14 fixes (cover art, audio range, interactive guide, the
console-error regression). Keeping them isolated means a regression
in the older test suite doesn't shadow the new surface tests.

Import from test_ui_full_ux.py's main() (via dynamic import) so the
existing runner still works.
"""
from __future__ import annotations

import re
import urllib.error
import urllib.request

# Local copy of the Suite / Result helpers from test_ui_full_ux.py to
# avoid coupling on private implementation details.
class Result:
    __slots__ = ("name", "ok", "detail")
    def __init__(self, name: str, ok: bool, detail: str = ""):
        self.name = name
        self.ok = bool(ok)
        self.detail = detail


class Suite:
    def __init__(self, name: str):
        self.name = name
        self.results: list[Result] = []

    def check(self, name: str, cond, detail: str = ""):
        self.results.append(Result(name, bool(cond), detail))

    def passed(self) -> int:
        return sum(1 for r in self.results if r.ok)

    def total(self) -> int:
        return len(self.results)

    def report(self) -> str:
        out = [f"\n=== {self.name}: {self.passed()}/{self.total()} passed ==="]
        for r in self.results:
            mark = "PASS" if r.ok else "FAIL"
            detail = f" ({r.detail})" if r.detail and not r.ok else ""
            out.append(f"  [{mark}] {r.name}{detail}")
        return "\n".join(out)


def _api(method: str, path: str, base: str, data=None):
    """HTTP client. Returns (status_code, parsed_body_or_text)."""
    import json
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        f"{base}{path}", data=body, method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            raw = r.read().decode()
            try:
                return r.status, json.loads(raw) if raw else None
            except Exception:
                return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw) if raw else None
        except Exception:
            return e.code, raw


def suite_cover_art(base: str) -> Suite:
    """Day 13: /api/albums/<id>/cover streams real JPEGs.

    The seed (db/seed.py) records cover_path relative to the
    OneDrive canonical per R10. The handler must fall back to
    OneDrive when no local file exists (commit 493f186).
    """
    s = Suite("Cover art (Day 13)")
    try:
        with urllib.request.urlopen(f"{base}/api/albums/half-light-hours/cover", timeout=10) as r:
            body = r.read()
            s.check("GET /api/albums/half-light-hours/cover → 200",
                    r.status == 200, f"got {r.status}")
            s.check("Content-Type is image/*",
                    r.headers.get("Content-Type", "").startswith("image/"),
                    f"got {r.headers.get('Content-Type', '')!r}")
            # JPEG magic bytes: FF D8 FF (also valid for JFIF / Exif / MP3+ID3)
            is_jpeg = body[:3] == b'\xff\xd8\xff'
            s.check("body has valid JPEG magic (FF D8 FF)",
                    is_jpeg, f"got {body[:4].hex()}")
            # Real covers are > 50KB (the album cover is 694KB)
            s.check("body size > 50KB (real cover, not placeholder)",
                    len(body) > 50_000, f"got {len(body)} bytes")
    except Exception as e:
        s.check("cover endpoint reachable", False, str(e))

    # Album row carries cover_path so the studio's <img> can resolve
    code, body = _api("GET", "/api/albums/half-light-hours", base)
    s.check("/api/albums/<id> returns cover_path",
            isinstance(body, dict) and bool(body.get("cover_path")),
            f"got cover_path={body.get('cover_path')!r}")
    return s


def suite_audio_streaming(base: str) -> Suite:
    """Day 11+13: /api/audio/<track> supports HTTP Range + serves
    real MP3s from OneDrive canonical per R10.

    Without the OneDrive fallback chain added in commit 443a036,
    all 10 of Maren Sol's seeded tracks would return 404 — this
    suite is the regression guard.
    """
    s = Suite("Audio streaming (Day 11+13)")
    all_tracks_ok = 0
    track_results = []
    for n in range(1, 11):
        tid = f"half-light-hours:{n:02d}"
        try:
            req = urllib.request.Request(
                f"{base}/api/audio/{tid}",
                headers={"Range": "bytes=0-1023"},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                if r.status == 206 and r.headers.get("Content-Range", "").startswith("bytes 0-"):
                    all_tracks_ok += 1
                    track_results.append(f"{tid}:OK")
                else:
                    track_results.append(f"{tid}:s={r.status}")
        except urllib.error.HTTPError as e:
            track_results.append(f"{tid}:HTTP{e.code}")
        except Exception as e:
            track_results.append(f"{tid}:ERR")
    s.check("all 10 tracks stream 206 Partial Content with Range",
            all_tracks_ok == 10,
            f"got {all_tracks_ok}/10 — {', '.join(track_results)}")

    # First track: Dusk Index valid MP3 ID3 header
    try:
        with urllib.request.urlopen(f"{base}/api/audio/half-light-hours:01", timeout=10) as r:
            body = r.read()
            has_id3 = body[:3] == b"ID3"
            s.check("Track 1 'Dusk Index' has valid MP3 ID3 header",
                    has_id3, f"got {body[:3]!r}")
            s.check("Track 1 size > 1MB (real audio, not stub)",
                    len(body) > 1_000_000, f"got {len(body)} bytes")
    except Exception as e:
        s.check("Track 1 reachable", False, str(e))

    # Title track: Half-Light Hours, larger
    try:
        with urllib.request.urlopen(f"{base}/api/audio/half-light-hours:03", timeout=15) as r:
            body = r.read()
            s.check("Track 3 'Half-Light Hours' (title) size > 1MB",
                    len(body) > 1_000_000, f"got {len(body)} bytes")
    except Exception as e:
        s.check("Track 3 reachable", False, str(e))

    return s


def suite_guide_overlay(base: str) -> Suite:
    """Day 13: interactive user guide overlay (4 steps, click-follow)."""
    s = Suite("Interactive guide overlay (Day 13)")
    code, body = _api("GET", "/site/studio.html", base)
    s.check("GET /site/studio.html → 200", code == 200, f"got {code}")
    if code == 200 and isinstance(body, str):
        s.check("studio.html includes /site/studio.guide.js",
                "studio.guide.js" in body, "guide script not loaded")
        s.check("studio.html includes ❓ HELP button",
                'id="help-btn"' in body, "help button missing")

    code, body = _api("GET", "/site/studio.guide.js", base)
    s.check("GET /site/studio.guide.js → 200", code == 200, f"got {code}")
    if code == 200 and isinstance(body, str):
        # 4 steps expected per docs/USER_MANUAL.md §5.1
        for step in ("invoke-brief", "play-track", "pause-session", "lock-decision"):
            s.check(f"guide.js has step '{step}'",
                    f"id: '{step}'" in body, "missing")
        s.check("guide.js uses localStorage('studio-guide-seen')",
                "studio-guide-seen" in body, "missing seen key")
        s.check("guide.js handles 'studio:show-guide' event",
                "studio:show-guide" in body, "missing event listener")
    return s


def suite_track_count(base: str) -> Suite:
    """Day 13: /api/albums decorates each row with track_count.

    The library.js cassette wall reads track_count from /api/albums
    to render "N TRACKS" in the eyebrow. Without the decoration
    (added in commit 493f186), the wall showed "Tracks: ?".
    """
    s = Suite("Track count decoration (Day 13)")
    code, body = _api("GET", "/api/albums", base)
    s.check("GET /api/albums → 200", code == 200, f"got {code}")
    # Handle both {count, items} and flat list shapes
    items = body.get("items") if isinstance(body, dict) else body
    if isinstance(items, list) and items:
        row = items[0]
        s.check("/api/albums returns track_count for half-light-hours",
                row.get("track_count") == 10,
                f"got track_count={row.get('track_count')!r}")
    return s


def suite_theme_switcher(base: str) -> Suite:
    """Day 15 (hour 1): theme switcher assets + wiring.

    The Omarchy-inspired theme switcher is a small floating dock
    in the bottom-left of every page. Each page must load
    /site/themes.css + /site/themes.js. The 4 themes must each
    have a :root[data-theme="..."] block in themes.css.
    """
    s = Suite("Theme switcher (Day 15 hour 1)")
    for asset, kind in [("/site/themes.css", "text/css"),
                        ("/site/themes.js", "javascript")]:
        try:
            with urllib.request.urlopen(f"{base}{asset}", timeout=5) as r:
                body = r.read().decode()
                s.check(f"GET {asset} → 200",
                        r.status == 200, f"got {r.status}")
                ct = r.headers.get("Content-Type", "")
                s.check(f"{asset} Content-Type is {kind}",
                        kind in ct, f"got {ct!r}")
        except Exception as e:
            s.check(f"{asset} reachable", False, str(e))

    # themes.css must define all 4 themes
    try:
        with urllib.request.urlopen(f"{base}/site/themes.css", timeout=5) as r:
            css = r.read().decode()
        for theme in ("mixtape85", "tokyonight", "catppuccin", "gruvbox"):
            # Each theme block must contain the 4 key semantic vars.
            # Use a forgiving pattern that handles whitespace + comments
            # (we strip line comments before matching).
            css_nocomments = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
            block_match = re.search(
                rf':root\[data-theme="{theme}"\]\s*\{{([^}}]+)\}}',
                css_nocomments, re.DOTALL,
            )
            if not block_match:
                s.check(f"theme '{theme}' has CSS block", False,
                        "no :root[data-theme=...] block found")
                continue
            block = block_match.group(1)
            for var in ("--bg", "--bg-soft", "--ink", "--accent"):
                s.check(f"theme '{theme}' defines {var}",
                        var in block,
                        f"missing {var} (block len={len(block)})")
    except Exception as e:
        s.check("themes.css readable", False, str(e))

    # Every page must load both assets
    for page in ("/site/studio.html", "/site/albums.html", "/site/library.html"):
        try:
            with urllib.request.urlopen(f"{base}{page}", timeout=5) as r:
                html = r.read().decode()
            s.check(f"{page} loads themes.css",
                    "/site/themes.css" in html, "missing link")
            s.check(f"{page} loads themes.js",
                    "/site/themes.js" in html, "missing script")
        except Exception as e:
            s.check(f"{page} reachable", False, str(e))

    return s


def run_all(base: str) -> int:
    """Run all 4 day-13/14 suites; return 0 if all pass, 1 otherwise."""
    suites = [
        suite_cover_art(base),
        suite_audio_streaming(base),
        suite_guide_overlay(base),
        suite_track_count(base),
        suite_theme_switcher(base),
    ]
    total_pass = total_fail = 0
    all_ok = True
    for suite in suites:
        print(suite.report())
        total_pass += suite.passed()
        total_fail += suite.total() - suite.passed()
        if suite.passed() != suite.total():
            all_ok = False

    print(f"\n=== Day 13-14 surfaces: {total_pass}/{total_pass + total_fail} passed ===")
    return 0 if all_ok else 1


if __name__ == "__main__":
    import os
    import sys
    base = os.environ.get("ALBUM_STUDIO_E2E_BASE", "http://127.0.0.1:8793")
    sys.exit(run_all(base))
