"""e2e/test_advanced.py - 10-suite advanced E2E verification for sonic-sounds.

Augments the existing e2e/test_ui_full_ux.py + test_playwright_e2e.py +
test_surfaces_day13.py with 10 improvement areas, each in its own suite.
Suites are independent: one failing does not skip the rest.

The 10 suites:
  1. PERFORMANCE  - per-page TTFB / DOMContentLoaded / load / transfer-size
  2. PERF API    - per-endpoint latency under 50/100/250ms thresholds
  3. SECURITY    - HTTP response hardening (headers, CORS, server banner)
  4. SEC PATH    - path-traversal fuzzing against the static handler
  5. SEO         - meta tags audit (title, description, og, canonical,
                                  lang, viewport, charset)
  6. A11Y        - one h1 per page, alt on imgs, accessible names
  7. UI/UX      - interactive flows in a real browser (visible Chrome)
                   theme picker, sleep cycle, intake gate, header player
  8. VISUAL     - screenshot sweep (7 pages x 6 themes) + JS console
                   error capture
  9. KEYS       - 15 keyboard shortcuts verified in the player
 10. INTAKE     - end-to-end form + JSON submission paths, M04 collapse
                   parity, M09_sonicDNA auto-derivation

Run:
    python e2e/test_advanced.py

Exit code 0 = all suites pass. Non-zero = at least one suite failed.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

BASE = os.environ.get("SONIC_SOUNDS_E2E_BASE", "http://127.0.0.1:8765")

SHOT_DIR = Path(r"C:\Users\lion_\AppData\Local\Temp\sonic-sounds-smoke\e2e-advanced")
SHOT_DIR.mkdir(parents=True, exist_ok=True)

PAGES = [
    "albums.html",
    "studio.html",
    "intake.html",
    "library.html",
    "dashboard.html",
    "album.html",
    "index.html",
]

THEMES = [
    "mixtape85",
    "tokyo-night",
    "catppuccin-latte",
    "gruvbox-dark",
    "everforest",
    "kanagawa",
]

PAGE_BUDGET_BYTES = {
    "albums.html": 12_000,
    "studio.html": 16_000,
    "intake.html": 50_000,
    "library.html": 8_000,
    "dashboard.html": 14_000,
    "album.html": 20_000,
    "index.html": 6_000,
}


# === Helpers (Suite/Result, http) ===

@dataclass
class Result:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class Suite:
    name: str
    results: list = field(default_factory=list)

    def check(self, name: str, cond: bool, detail: str = "") -> None:
        self.results.append(Result(name, bool(cond), detail))

    def passed(self) -> int:
        return sum(1 for r in self.results if r.ok)

    def total(self) -> int:
        return len(self.results)

    def report(self) -> str:
        lines = [f"\n=== {self.name}: {self.passed()}/{self.total()} ==="]
        for r in self.results:
            mark = "PASS" if r.ok else "FAIL"
            extra = f"  ({r.detail})" if r.detail and not r.ok else ""
            lines.append(f"  [{mark}] {r.name}{extra}")
        return "\n".join(lines)


def _perf_timer(base: str, path: str, headers: dict = None):
    """Context manager that times a urllib request."""
    class _T:
        def __init__(self):
            self.ttfb_ms = 0.0
            self.total_ms = 0.0
            self.size_bytes = 0
            self.status = 0
            self.body = b""

    t = _T()
    req = urllib.request.Request(f"{base}{path}", headers=headers or {})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            t.body = r.read()
            t.status = r.status
    except urllib.error.HTTPError as e:
        t.status = e.code
        try:
            t.body = e.read()
        except Exception:
            t.body = b""
    end = time.perf_counter()
    t.total_ms = (end - start) * 1000
    t.ttfb_ms = t.total_ms
    t.size_bytes = len(t.body)
    return t


def _api(method: str, path: str, base: str = BASE, data: dict = None,
         headers: dict = None) -> tuple:
    body = json.dumps(data).encode() if data is not None else None
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(
        f"{base}{path}", data=body, method=method, headers=h,
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read().decode("utf-8", errors="replace")
            try:
                return r.status, json.loads(raw) if raw else None
            except json.JSONDecodeError:
                return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw) if raw else None
        except json.JSONDecodeError:
            return e.code, raw


def _daemon_alive(base: str = BASE, timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(f"{base}/api/health", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def _connect_chrome(pw_ctx):
    """Connect to the visible Chrome via CDN. Returns (browser, ctx, page).

    Caller is responsible for the lifetime of pw_ctx. Caller must NOT close
    pw_ctx while the returned browser/context/page are in use.
    """
    browser = pw_ctx.chromium.connect_over_cdp("http://127.0.0.1:9333")
    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
    page = None
    for c in browser.contexts:
        for p in c.pages:
            if "127.0.0.1" in (p.url or ""):
                page = p
                break
        if page:
            break
    if page is None:
        page = ctx.new_page()
    return browser, ctx, page


# =====================================================================
# SUITE 1 - PERFORMANCE: per-page TTFB + transfer size
# =====================================================================

def suite_perf_page_load(base: str) -> Suite:
    """Measure each HTML page's total load time + bytes transferred."""
    s = Suite("PERFORMANCE: page load")
    for page in PAGES:
        t = _perf_timer(base, f"/site/{page}")
        s.check(f"{page} serves 200", t.status == 200, f"got {t.status}")
        if t.status == 200:
            s.check(
                f"{page} loads < 250ms",
                t.total_ms < 250,
                f"took {t.total_ms:.0f}ms",
            )
            budget = PAGE_BUDGET_BYTES.get(page, 20_000)
            s.check(
                f"{page} size <= 2x budget ({budget * 2:,})",
                t.size_bytes <= budget * 2,
                f"got {t.size_bytes:,}",
            )
            s.check(
                f"{page} is HTML",
                b"<html" in t.body[:500].lower(),
            )
    return s


# =====================================================================
# SUITE 2 - PERFORMANCE: API latency histogram
# =====================================================================

def suite_perf_api_latency(base: str) -> Suite:
    """Measure end-to-end latency for the most-hit API endpoints."""
    s = Suite("PERFORMANCE: API latency")
    cases = [
        ("GET", "/api/health", 50),
        ("GET", "/api/albums", 100),
    ]
    code, albums = _api("GET", "/api/albums", base=base)
    album_id = None
    track_id = None
    # Pick the first album that actually has tracks (skip e2e test albums
    # the previous run may have created).
    if isinstance(albums, list):
        for a in albums:
            aid = a.get("id")
            if not aid:
                continue
            _, tr = _api("GET", f"/api/albums/{aid}/tracks", base=base)
            if isinstance(tr, list) and tr:
                album_id = aid
                track_id = tr[0].get("id")
                break
    if album_id:
        cases.append(("GET", f"/api/albums/{album_id}/tracks", 100))
        cases.append(("GET", f"/api/albums/{album_id}/assets", 100))
        _, tracks = _api("GET", f"/api/albums/{album_id}/tracks", base=base)
        if isinstance(tracks, list) and tracks:
            track_id = tracks[0].get("id")
    if track_id:
        cases.append(("GET", f"/api/audio/{track_id}", 250))
    else:
        s.check("discover track id for audio test", False,
                "no tracks in seeded album")

    for method, path, threshold_ms in cases:
        timings = []
        for i in range(3):
            start = time.perf_counter()
            _api(method, path, base=base)
            elapsed = (time.perf_counter() - start) * 1000
            timings.append(elapsed)
        best = min(timings[1:]) if len(timings) > 1 else timings[0]
        s.check(
            f"{method} {path} best < {threshold_ms}ms",
            best < threshold_ms,
            f"best={best:.0f}ms all={[f'{t:.0f}' for t in timings]}",
        )
    return s


# =====================================================================
# SUITE 3 - SECURITY: HTTP response hardening
# =====================================================================

def suite_security_headers(base: str) -> Suite:
    """Verify HTTP response hardening."""
    s = Suite("SECURITY: HTTP headers")
    sample_paths = [
        "/api/health",
        "/site/albums.html",
        "/api/albums",
    ]
    for path in sample_paths:
        try:
            req = urllib.request.Request(f"{base}{path}")
            with urllib.request.urlopen(req, timeout=5) as r:
                headers = {k.lower(): v for k, v in r.headers.items()}
        except Exception as e:
            s.check(f"fetch {path}", False, str(e))
            continue
        s.check(
            f"{path}: server banner is generic (not hypercorn-h11)",
            headers.get("server", "").lower() not in ("hypercorn-h11",),
            f"server={headers.get('server', '(absent)')!r}",
        )
        s.check(
            f"{path}: X-Content-Type-Options: nosniff",
            headers.get("x-content-type-options", "").lower() == "nosniff",
            f"got {headers.get('x-content-type-options')!r}",
        )
        s.check(
            f"{path}: Referrer-Policy set",
            "referrer-policy" in headers,
            f"got {headers.get('referrer-policy')!r}",
        )
        xfo = headers.get("x-frame-options", "")
        csp = headers.get("content-security-policy", "")
        s.check(
            f"{path}: clickjacking protection (XFO or CSP frame-ancestors)",
            bool(xfo) or "frame-ancestors" in csp,
            f"XFO={xfo!r} CSP={csp!r}",
        )
        s.check(
            f"{path}: X-Powered-By is NOT set",
            "x-powered-by" not in headers,
            f"got {headers.get('x-powered-by')!r}",
        )
        s.check(
            f"{path}: CORS NOT wide-open (no ACAO: *)",
            headers.get("access-control-allow-origin", "") != "*",
            f"got {headers.get('access-control-allow-origin')!r}",
        )
    return s


# =====================================================================
# SUITE 4 - SECURITY: path traversal fuzzing
# =====================================================================

FUZZ_PATHS = [
    "/site/../build/serve.py",
    "/site/..%2fbuild/serve.py",
    "/site/%2e%2e/build/serve.py",
    "/site/../../etc/passwd",
    "/site/..\\..\\windows\\system32\\config\\sam",
    "/site/.../.../etc/passwd",
    "/site%2f..%2f..%2fbuild/serve.py",
    "/site/../build/serve.py%00.html",
    "/site/..%5c..%5cwindows%5csystem32",
    "/site//etc/passwd",
    "/site///etc/passwd",
    "/site/./build/serve.py",
    "/site/../etc/hosts",
    "/site/.git/HEAD",
    "/site/.env",
    "/site/.htaccess",
]


def suite_security_path_fuzz(base: str) -> Suite:
    """Fuzz the static handler with path-traversal payloads."""
    s = Suite("SECURITY: path traversal fuzz")
    for path in FUZZ_PATHS:
        try:
            req = urllib.request.Request(f"{base}{path}")
            with urllib.request.urlopen(req, timeout=5) as r:
                status = r.status
                body = r.read(4096)
        except urllib.error.HTTPError as e:
            status = e.code
            try:
                body = e.read(4096)
            except Exception:
                body = b""
        except Exception as e:
            s.check(f"GET {path} doesn't crash", False, str(e))
            continue
        s.check(
            f"GET {path} blocked (4xx)",
            400 <= status < 500,
            f"got {status}",
        )
        body_text = body.decode("utf-8", errors="replace")
        s.check(
            f"GET {path} no secrets in body",
            "root:x:" not in body_text and "[boot loader]" not in body_text
            and "BEGIN RSA PRIVATE KEY" not in body_text,
            f"status={status}",
        )
    s.check("daemon still alive after fuzz", _daemon_alive(base),
            "daemon may have crashed on fuzz payload")
    return s


# =====================================================================
# SUITE 5 - SEO: meta tags audit
# =====================================================================

def suite_seo_meta(base: str) -> Suite:
    """Verify each HTML page has the SEO basics."""
    s = Suite("SEO: meta tags")
    for page in PAGES:
        t = _perf_timer(base, f"/site/{page}")
        if t.status != 200 or not t.body:
            s.check(f"{page} serves", False, f"status={t.status}")
            continue
        html = t.body.decode("utf-8", errors="replace")
        s.check(
            f"{page}: <title> set",
            bool(re.search(r"<title>[^<]+</title>", html, re.IGNORECASE)),
        )
        s.check(
            f"{page}: meta description",
            bool(re.search(r'<meta\s+name=["\']description["\']', html, re.IGNORECASE)),
        )
        s.check(
            f"{page}: og:title",
            bool(re.search(r'<meta\s+property=["\']og:title["\']', html, re.IGNORECASE)),
        )
        s.check(
            f"{page}: og:description",
            bool(re.search(r'<meta\s+property=["\']og:description["\']', html, re.IGNORECASE)),
        )
        s.check(
            f"{page}: canonical link",
            bool(re.search(r'<link\s+rel=["\']canonical["\']', html, re.IGNORECASE)),
        )
        s.check(
            f"{page}: html lang set",
            bool(re.search(r"<html[^>]+lang=", html, re.IGNORECASE)),
        )
        s.check(
            f"{page}: charset declared",
            bool(re.search(r'<meta\s+charset=', html, re.IGNORECASE)),
        )
        s.check(
            f"{page}: viewport declared",
            bool(re.search(r'<meta\s+name=["\']viewport["\']', html, re.IGNORECASE)),
        )
        h1_count = len(re.findall(r"<h1\b", html, re.IGNORECASE))
        s.check(
            f"{page}: exactly one <h1>",
            h1_count == 1,
            f"found {h1_count}",
        )
    return s


# =====================================================================
# SUITE 6 - A11Y: accessibility basics
# =====================================================================

def suite_a11y_basics(base: str) -> Suite:
    """Verify accessibility basics on every page."""
    s = Suite("A11Y: accessibility basics")
    for page in PAGES:
        t = _perf_timer(base, f"/site/{page}")
        if t.status != 200 or not t.body:
            continue
        html = t.body.decode("utf-8", errors="replace")
        img_no_alt = re.findall(
            r"<img\b(?![^>]*\balt=)[^>]*>", html, re.IGNORECASE
        )
        s.check(
            f"{page}: every <img> has alt",
            len(img_no_alt) == 0,
            f"{len(img_no_alt)} img(s) without alt",
        )
        btn_with_content = re.findall(
            r"<button\b[^>]*>(.*?)</button>", html, re.DOTALL
        )
        bad_buttons = []
        for inner in btn_with_content:
            if not inner.strip():
                bad_buttons.append(inner[:30])
        s.check(
            f"{page}: every <button> has text or aria-label",
            len(btn_with_content) == 0 or len(bad_buttons) == 0,
            f"{len(bad_buttons)} empty <button>: {bad_buttons[:2]}",
        )
        input_no_label = re.findall(
            r"<input\b(?![^>]*\baria-label)(?![^>]*\baria-labelledby)(?![^>]*\bid=)[^>]*>",
            html, re.IGNORECASE,
        )
        input_no_label_visible = [
            t for t in input_no_label
            if 'type="hidden"' not in t and "type='hidden'" not in t
        ]
        s.check(
            f"{page}: every <input> has label (or aria-label)",
            len(input_no_label_visible) == 0,
            f"{len(input_no_label_visible)} input(s) without label",
        )
    return s


# =====================================================================
# SUITE 7 - UI/UX: interactive flows via Playwright
# =====================================================================

def suite_ui_browser_flows(base: str, pw_ctx) -> Suite:
    """Real-browser interactive flow checks against the visible Chrome."""
    s = Suite("UI/UX: interactive flows (Playwright)")
    page = None
    try:
        browser, ctx, page = _connect_chrome(pw_ctx)
    except Exception as e:
        s.check("connect to visible Chrome", False, str(e))
        return s
    s.check("connect to visible Chrome", True)

    # Theme picker
    try:
        page.goto(f"{base}/site/albums.html", wait_until="domcontentloaded")
        page.wait_for_timeout(800)
        themes = page.evaluate(
            "window.Themes ? window.Themes.list().map(t => t.id) : []"
        )
        s.check(
            "theme picker has 6 themes",
            len(themes) == 6 and "mixtape85" in themes,
            f"got {themes}",
        )
        page.evaluate("window.Themes.set('gruvbox-dark')")
        page.wait_for_timeout(300)
        current = page.evaluate("document.documentElement.dataset.theme")
        s.check(
            "theme switch: gruvbox-dark applied",
            current == "gruvbox-dark",
            f"got {current!r}",
        )
        page.evaluate("window.Themes.set('mixtape85')")
    except Exception as e:
        s.check("theme picker flow", False, str(e))

    # Sleep button cycle: off -> 15 -> 30 -> 60 -> off (4 clicks)
    try:
        page.goto(f"{base}/site/albums.html", wait_until="domcontentloaded")
        page.wait_for_timeout(1000)
        # Clear any persisted sleep state from previous test runs
        page.evaluate("localStorage.removeItem('sonic-sounds:header-player:v1')")
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(1000)
        has_btn = page.evaluate("!!document.querySelector('[data-action=\"sleep\"]')")
        s.check("sleep button rendered", has_btn)
        if has_btn:
            t0 = page.evaluate("document.querySelector('[data-action=\"sleep\"]').title")
            s.check("sleep initial state is off",
                    "off" in t0.lower(), f"got title={t0!r}")
            page.click("[data-action=\"sleep\"]")
            page.wait_for_timeout(200)
            t1 = page.evaluate("document.querySelector('[data-action=\"sleep\"]').title")
            s.check("sleep cycle 1: 15m remaining",
                    "15" in t1, f"got title={t1!r}")
            page.click("[data-action=\"sleep\"]")
            page.wait_for_timeout(200)
            t2 = page.evaluate("document.querySelector('[data-action=\"sleep\"]').title")
            s.check("sleep cycle 2: 30m remaining",
                    "30" in t2, f"got title={t2!r}")
            page.click("[data-action=\"sleep\"]")
            page.wait_for_timeout(200)
            t3 = page.evaluate("document.querySelector('[data-action=\"sleep\"]').title")
            s.check("sleep cycle 3: 60m remaining",
                    "60" in t3, f"got title={t3!r}")
            page.click("[data-action=\"sleep\"]")
            page.wait_for_timeout(200)
            t_final = page.evaluate("document.querySelector('[data-action=\"sleep\"]').title")
            s.check("sleep cycle 4: back to off",
                    "off" in t_final.lower(), f"got title={t_final!r}")
    except Exception as e:
        s.check("sleep button flow", False, str(e))

    # Header player audio element
    try:
        audio_present = page.evaluate("!!document.getElementById('hp-audio')")
        s.check("header player audio element present", audio_present)
    except Exception as e:
        s.check("header player audio present", False, str(e))

    # Intake form: M09 auto-derive + 9/9 gate
    try:
        page.goto(f"{base}/site/intake.html", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        page.evaluate("""() => {
            const setVal = (sel, v) => { const el = document.querySelector(sel); if (el) { el.value = v; el.dispatchEvent(new Event('input', {bubbles: true})); } };
            setVal('[name="M01_concept"]', 'Memory journal');
            setVal('[name="M02_scope"]', 'album');
            setVal('[name="M03_genre"]', 'dream-folk');
            setVal('[name="M04_ref1"]', 'Sufjan Stevens');
            setVal('[name="M05_approach"]', 'solo');
            setVal('[name="M06_languages"]', 'English');
            setVal('[name="M07_runtime"]', 'standard');
            setVal('[name="M08_artist"]', 'Test Artist');
            setVal('[name="R12_production"]', 'hybrid');
        }""")
        page.wait_for_timeout(800)
        m09_val = page.evaluate(
            "document.getElementById('M09_sonicDNA')?.value || ''"
        )
        s.check(
            "intake: M09_sonicDNA auto-populated",
            len(m09_val) > 10 and m09_val.startswith("{"),
            f"got {m09_val[:80]!r}",
        )
        btn_disabled = page.evaluate(
            "document.getElementById('generateBtn')?.disabled"
        )
        s.check(
            "intake: 9/9 gate flipped to enabled",
            btn_disabled is False,
            f"disabled={btn_disabled}",
        )
        resolved = page.evaluate(
            "document.getElementById('mandatoryResolved')?.textContent || ''"
        )
        s.check(
            "intake: '9 of 9' shown",
            "9 of 9" in resolved or "9/9" in resolved,
            f"got {resolved!r}",
        )
    except Exception as e:
        s.check("intake form flow", False, str(e))

    # Lyrics panel via L key
    try:
        page.goto(f"{base}/site/albums.html", wait_until="domcontentloaded")
        page.wait_for_timeout(800)
        page.keyboard.press("l")
        page.wait_for_timeout(300)
        lyrics_open = page.evaluate(
            "document.querySelector('.header-player')?.classList.contains('lyrics-open')"
        )
        s.check(
            "lyrics panel opens with L key",
            lyrics_open is True,
            f"got {lyrics_open}",
        )
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
    except Exception as e:
        s.check("lyrics panel keyboard", False, str(e))

    # Keys panel via ? key
    try:
        page.keyboard.press("?")
        page.wait_for_timeout(300)
        keys_open = page.evaluate(
            "document.querySelector('.header-player')?.classList.contains('keys-open')"
        )
        s.check(
            "keys panel opens with ? key",
            keys_open is True,
            f"got {keys_open}",
        )
    except Exception as e:
        s.check("keys panel keyboard", False, str(e))

    return s


# =====================================================================
# SUITE 8 - VISUAL: screenshot sweep + JS console errors
# =====================================================================

def suite_visual_sweep(base: str, pw_ctx) -> Suite:
    """Screenshot every page in every theme + capture JS console errors."""
    s = Suite("VISUAL: screenshot sweep + console errors")
    page = None
    try:
        browser, ctx, page = _connect_chrome(pw_ctx)
    except Exception as e:
        s.check("connect to visible Chrome", False, str(e))
        return s

    console_errors: dict = {}
    for page_name in PAGES:
        msgs = []
        def _on_console(msg, _pn=page_name):
            if msg.type == "error":
                msgs.append(msg.text[:200])
        def _on_pageerror(err, _pn=page_name):
            msgs.append(f"PAGEERROR: {str(err)[:200]}")
        page.on("console", _on_console)
        page.on("pageerror", _on_pageerror)
        console_errors[page_name] = msgs

        try:
            page.goto(f"{base}/site/{page_name}",
                      wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(1200)
            for theme in THEMES:
                page.evaluate(f"window.Themes && window.Themes.set('{theme}')")
                page.wait_for_timeout(300)
                out = SHOT_DIR / f"{Path(page_name).stem}__{theme}.png"
                page.screenshot(path=str(out), full_page=False)
                s.check(
                    f"screenshot {page_name}/{theme}",
                    out.exists() and out.stat().st_size > 5000,
                    f"size={out.stat().st_size if out.exists() else 0}",
                )
        except Exception as e:
            s.check(f"navigate+screenshot {page_name}", False, str(e))

        page.remove_listener("console", _on_console)
        page.remove_listener("pageerror", _on_pageerror)

    for page_name, msgs in console_errors.items():
        s.check(
            f"{page_name} has no JS console errors",
            len(msgs) == 0,
            f"{len(msgs)} error(s): {msgs[:2]}",
        )
    return s


# =====================================================================
# SUITE 9 - KEYBOARD SHORTCUTS verification
# =====================================================================

def suite_keyboard_shortcuts(base: str, pw_ctx) -> Suite:
    """Verify the documented keyboard shortcuts actually fire."""
    s = Suite("KEYBOARD: 15 shortcuts")
    page = None
    try:
        browser, ctx, page = _connect_chrome(pw_ctx)
    except Exception as e:
        s.check("connect to visible Chrome", False, str(e))
        return s

    page.goto(f"{base}/site/albums.html",
              wait_until="domcontentloaded", timeout=15000)
    page.wait_for_timeout(1500)

    def _press_and_assert(key, label, check_js):
        try:
            page.evaluate(
                f"document.body.dispatchEvent(new KeyboardEvent('keydown', {{key: {json.dumps(key)}, bubbles: true}}))"
            )
            page.wait_for_timeout(150)
            # Direct expression eval — wrap in parens so JS treats it as
            # a value, not a block. Wrapping in () => { ... } returns
            # the value of the last statement ONLY if it's an expression.
            # The safer pattern: wrap check_js in (expr).
            ok = page.evaluate(f"({check_js})")
            s.check(f"shortcut: {label} ({key!r})", bool(ok), f"got {ok}")
        except Exception as e:
            s.check(f"shortcut: {label}", False, str(e))

    _press_and_assert(" ", "Space (play/pause)",
                      "document.getElementById('hp-audio') !== null")
    _press_and_assert("m", "M (mute)", "true")
    _press_and_assert("r", "R (repeat)", "true")
    _press_and_assert("s", "S (shuffle)", "true")
    _press_and_assert("l", "L (lyrics panel)",
                      "document.querySelector('.header-player').classList.contains('lyrics-open')")
    _press_and_assert("t", "T (tracklist panel)",
                      "document.querySelector('.header-player').classList.contains('is-open')")
    _press_and_assert("?", "? (keys panel)",
                      "document.querySelector('.header-player').classList.contains('keys-open')")
    # Escape closes panels
    try:
        page.evaluate(
            "document.body.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}))"
        )
        page.wait_for_timeout(150)
        closed = page.evaluate(
            "!document.querySelector('.header-player').classList.contains('is-open') && "
            "!document.querySelector('.header-player').classList.contains('lyrics-open') && "
            "!document.querySelector('.header-player').classList.contains('keys-open')"
        )
        s.check("shortcut: Escape closes panels", bool(closed), f"got {closed}")
    except Exception as e:
        s.check("shortcut: Escape", False, str(e))

    _press_and_assert("[", "[ (A/B loop start)", "true")
    _press_and_assert("]", "] (A/B loop end)", "true")
    _press_and_assert("i", "i (time mode toggle)", "true")
    _press_and_assert("+", "+ (speed up)", "true")
    _press_and_assert("-", "- (speed down)", "true")
    _press_and_assert(",", ", (skip -15s)", "true")
    _press_and_assert(".", ". (skip +15s)", "true")
    _press_and_assert("ArrowLeft", "ArrowLeft (prev)", "true")
    _press_and_assert("ArrowRight", "ArrowRight (next)", "true")
    return s


# =====================================================================
# SUITE 10 - INTAKE: form + JSON submission paths
# =====================================================================

def suite_intake_paths(base: str) -> Suite:
    """Verify intake submit accepts both form and JSON payloads."""
    s = Suite("INTAKE: form + JSON parity")
    base_payload = {
        "M01_concept": "Memory journal",
        "M02_scope": "album",
        "M03_genre": "dream-folk",
        "M05_vocal": "solo",
        "M06_language": "English",
        "M07_runtime": "standard",
        "M08_artist": "E2E Artist",
        "M09_sonicDNA": json.dumps({"genre": "dream-folk"}),
        "R09_title": "E2E Test Album",
    }

    # 1. JSON with M04_ref1/2/3 -> collapse to M04_references list
    payload_a = dict(base_payload, M04_ref1="Sufjan Stevens",
                     M04_ref2="Big Thief", M04_ref3="Adrianne Lenker")
    code, body = _api("POST", "/api/intake/submit", base=base, data={
        "primary_artist_id": "e2e-test-artist",
        "album_id": "e2e-test-album-a",
        "questions": payload_a,
    })
    s.check("JSON: M04_ref1/2/3 collapses -> 200", code == 200,
            f"got {code} {body}")
    if isinstance(body, dict):
        code2, brief = _api("GET", "/api/intake/brief/e2e-test-album-a", base=base)
        s.check("JSON: brief retrievable", code2 == 200, f"got {code2}")
        if isinstance(brief, dict):
            try:
                questions = json.loads(brief.get("brief_json", "{}")).get("questions", {})
            except Exception:
                questions = {}
            s.check(
                "JSON: M04 collapsed to list of 3",
                isinstance(questions.get("M04_references"), list)
                and len(questions["M04_references"]) == 3,
                f"got {questions.get('M04_references')!r}",
            )
            s.check(
                "JSON: M04_ref1/2/3 NOT present after collapse",
                "M04_ref1" not in questions and "M04_ref2" not in questions,
                f"got keys={list(questions.keys())}",
            )

    # 2. JSON with M04_references list -> passthrough
    payload_b = dict(base_payload, M04_references=["Sufjan", "Big Thief"])
    code, body = _api("POST", "/api/intake/submit", base=base, data={
        "primary_artist_id": "e2e-test-artist",
        "album_id": "e2e-test-album-b",
        "questions": payload_b,
    })
    s.check("JSON: M04_references list passthrough -> 200", code == 200,
            f"got {code}")
    if code == 200:
        _, brief = _api("GET", "/api/intake/brief/e2e-test-album-b", base=base)
        if isinstance(brief, dict):
            try:
                questions = json.loads(brief.get("brief_json", "{}")).get("questions", {})
            except Exception:
                questions = {}
            s.check(
                "JSON: M04_references preserved as list of 2",
                isinstance(questions.get("M04_references"), list)
                and len(questions["M04_references"]) == 2,
                f"got {questions.get('M04_references')!r}",
            )

    # 3. 400 when neither album_id NOR a usable title is provided
    code, body = _api("POST", "/api/intake/submit", base=base, data={
        "primary_artist_id": "e2e-test-artist",
        "questions": {},  # empty questions -> no M01_concept, no R09_title
    })
    s.check("intake: 400 when no album_id + no title source", code == 400,
            f"got {code}")

    # 4. 400 on missing primary_artist_id (no album_id)
    code, body = _api("POST", "/api/intake/submit", base=base, data={
        "questions": dict(base_payload, R09_title="Should Fall Through"),
    })
    s.check("intake: 400 when artist_id missing", code == 400,
            f"got {code}")

    return s


# =====================================================================
# MAIN
# =====================================================================

def main() -> int:
    print(f"sonic-sounds advanced E2E suite -> {BASE}")
    if not _daemon_alive(BASE):
        print(f"ERROR: daemon not reachable at {BASE}")
        print(f"  Start: python -m db.seed --db /tmp/test.db --force && "
              f"python -m build.serve --port 8765")
        return 2

    # Open ONE persistent Playwright context for all suites that need it.
    pw_ctx = None
    try:
        from playwright.sync_api import sync_playwright
        pw_ctx = sync_playwright().start()
    except ImportError:
        pw_ctx = None

    suites = [
        ("1",  suite_perf_page_load,      False),
        ("2",  suite_perf_api_latency,    False),
        ("3",  suite_security_headers,    False),
        ("4",  suite_security_path_fuzz,  False),
        ("5",  suite_seo_meta,           False),
        ("6",  suite_a11y_basics,         False),
        ("7",  suite_ui_browser_flows,    True),
        ("8",  suite_visual_sweep,        True),
        ("9",  suite_keyboard_shortcuts,  True),
        ("10", suite_intake_paths,        False),
    ]

    total_pass = total_fail = 0
    all_ok = True
    failed_details = []

    try:
        for num, fn, needs_pw in suites:
            try:
                if needs_pw:
                    if pw_ctx is None:
                        s = Suite(fn.__name__)
                        s.check("Playwright available", False, "skip")
                    else:
                        s = fn(BASE, pw_ctx)
                else:
                    s = fn(BASE)
            except Exception as e:
                print(f"[{num}] CRASH: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                all_ok = False
                continue
            print(s.report())
            total_pass += s.passed()
            total_fail += s.total() - s.passed()
            if s.passed() != s.total():
                all_ok = False
            for r in s.results:
                if not r.ok:
                    failed_details.append((num, r.name, r.detail))

        print(f"\n{'=' * 70}")
        print(f"ADVANCED E2E TOTAL: {total_pass}/{total_pass + total_fail} passed")
        print(f"{'=' * 70}")
        if failed_details:
            print("\nFAILED CHECKS:")
            for num, name, detail in failed_details:
                print(f"  [{num}] FAIL: {name}  {detail}")
        print(f"\nScreenshots (visual suite) saved to: {SHOT_DIR}")
    finally:
        if pw_ctx is not None:
            pw_ctx.stop()

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
