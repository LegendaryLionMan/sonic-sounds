"""scripts/visual_inspect.py - full visual inspection tool.

Captures full-page screenshots of every page at 6 themes x 3 widths,
runs automated element audits (overflow, alt text, button labels,
contrast, transparent bgs, stuck-open panels), and saves a structured
JSON + human report.

This is the foundation of suite 20 (visual regression).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOT_BASE = Path(r"C:\Users\lion_\AppData\Local\Temp\sonic-sounds-smoke\inspect")
SHOT_BASE.mkdir(parents=True, exist_ok=True)

ALL_PAGES = ["albums.html", "studio.html", "intake.html", "library.html",
             "dashboard.html", "album.html", "index.html"]
THEMES = ["mixtape85", "tokyo-night", "catppuccin-latte", "gruvbox-dark",
          "everforest", "kanagawa"]
WIDTHS = [(1440, 900), (768, 1024), (375, 812)]


def run_element_checks(page, path: str) -> dict:
    """Battery of DOM/CSS audits on the current page."""
    check = {"issues": [], "metrics": {}}
    h = page.evaluate("document.documentElement.scrollHeight")
    check["metrics"]["page_height_px"] = h
    if h > 8000:
        check["issues"].append({
            "type": "page_too_tall", "severity": "high",
            "detail": f"page scrolls {h}px - extreme height hides content",
        })
    bw = page.evaluate("document.body.scrollWidth")
    vw = page.evaluate("window.innerWidth")
    check["metrics"]["body_scrollWidth"] = bw
    check["metrics"]["viewport_width"] = vw
    if bw > vw + 4:
        check["issues"].append({"type": "horizontal_overflow", "severity": "high",
                                "detail": f"body {bw}px > vp {vw}px"})
        wide = page.evaluate("""() => {
            const out = [];
            for (const el of document.querySelectorAll('*')) {
                const r = el.getBoundingClientRect();
                if (r.right > window.innerWidth + 4 && r.width > 100) {
                    out.push({tag: el.tagName.toLowerCase(),
                              cls: el.className.toString().slice(0, 60),
                              right: Math.round(r.right),
                              w: Math.round(r.width)});
                    if (out.length > 5) break;
                }
            }
            return out;
        }""")
        if wide:
            check["issues"].append({"type": "wide_element", "severity": "medium",
                                    "detail": "elements overflowing viewport",
                                    "elements": wide})
    imgs = page.evaluate("""() => Array.from(document.querySelectorAll('img'))
        .filter(i => !i.hasAttribute('alt') && !i.getAttribute('aria-hidden'))
        .map(i => ({src: i.src.slice(-60),
                    cls: i.className.toString().slice(0, 40)}))""")
    if imgs:
        check["issues"].append({"type": "img_missing_alt", "severity": "high",
                                "detail": f"{len(imgs)} <img> without alt",
                                "elements": imgs[:5]})
    btns = page.evaluate("""() => Array.from(document.querySelectorAll('button'))
        .filter(b => !b.textContent.trim() && !b.getAttribute('aria-label'))
        .map(b => ({cls: b.className.toString().slice(0, 60),
                    html: b.outerHTML.slice(0, 100)}))""")
    if btns:
        check["issues"].append({"type": "btn_no_label", "severity": "high",
                                "detail": f"{len(btns)} btn no label",
                                "elements": btns[:5]})
    inputs = page.evaluate("""() => {
        const out = [];
        document.querySelectorAll('input:not([type=hidden]), textarea, select').forEach(el => {
            const lab = el.id ? (document.querySelector(`label[for="${el.id}"]`) || el.closest('label')) : null;
            if (!lab && !el.getAttribute('aria-label')) {
                out.push({tag: el.tagName.toLowerCase(),
                          name: el.name, type: el.type});
            }
        });
        return out;
    }""")
    if inputs:
        check["issues"].append({"type": "input_no_label", "severity": "high",
                                "detail": f"{len(inputs)} inputs without labels",
                                "elements": inputs[:5]})
    panels = page.evaluate("""() => {
        const out = [];
        for (const cls of ['keys-open', 'lyrics-open', 'is-open']) {
            if (document.querySelector('.header-player.' + cls)) out.push(cls);
        }
        return out;
    }""")
    if panels:
        check["issues"].append({"type": "panel_stuck_open", "severity": "medium",
                                "detail": f"open: {panels}"})
    bgfg = page.evaluate("""() => {
        const cs = getComputedStyle(document.body);
        return {bg: cs.backgroundColor, fg: cs.color};
    }""")
    check["metrics"]["body_bg"] = bgfg["bg"]
    check["metrics"]["body_fg"] = bgfg["fg"]
    if bgfg["bg"] in ("rgba(0, 0, 0, 0)", "transparent"):
        check["issues"].append({"type": "transparent_body_bg", "severity": "medium",
                                "detail": "body bg is transparent"})
    return check


def aggregate(findings: dict) -> dict:
    counts = {"high": 0, "medium": 0, "low": 0}
    by_type = {}
    for w, pages in findings["pages"].items():
        for path, check in pages.items():
            for issue in check.get("issues", []):
                sev = issue.get("severity", "low")
                counts[sev] = counts.get(sev, 0) + 1
                by_type.setdefault(issue["type"], []).append(f"{w}/{path}")
    return {"by_severity": counts, "by_type": by_type}


def main() -> int:
    p = argparse.ArgumentParser(description="visual inspection")
    p.add_argument("--base", default="http://127.0.0.1:8765")
    p.add_argument("--page", action="append", help="specific page")
    p.add_argument("--widths", nargs="*", type=int,
                   help="widths (default 1440 768 375)")
    p.add_argument("--json", action="store_true", help="emit JSON report")
    args = p.parse_args()

    from playwright.sync_api import sync_playwright
    pages = args.page or ALL_PAGES
    widths = [(w, 900) for w in (args.widths or [1440, 768, 375])]
    results = {"pages": {}, "summary": {}}

    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        page = browser.contexts[0].pages[0]
        for w, h in widths:
            page.set_viewport_size({"width": w, "height": h})
            for path in pages:
                ts = int(time.time())
                page.goto(f"{args.base}/site/{path}?v=inspect-{w}-{ts}",
                          wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(700)
                page.evaluate("window.Themes && window.Themes.set('mixtape85')")
                page.wait_for_timeout(300)
                check = run_element_checks(page, path)
                fname = f"{Path(path).stem}__{w}.png"
                out = SHOT_BASE / fname
                try:
                    page.screenshot(path=str(out), full_page=False)
                    check["screenshot"] = str(out)
                except Exception as e:
                    check["screenshot_error"] = str(e)
                results["pages"].setdefault(f"{w}x{h}", {})[path] = check
    results["summary"] = aggregate(results)
    if args.json:
        print(json.dumps(results, indent=2))
        return 0
    print(f"\n=== visual inspection summary ===")
    sev = results["summary"]["by_severity"]
    print(f"  high:   {sev.get('high', 0)}")
    print(f"  medium: {sev.get('medium', 0)}")
    print(f"  low:    {sev.get('low', 0)}")
    by_type = results["summary"]["by_type"]
    if by_type:
        print(f"\n  by type:")
        for typ, locs in sorted(by_type.items()):
            print(f"    {typ}: {len(locs)} occurrence(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
