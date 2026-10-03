"""scripts/doc-snapshot - generate a static HTML snapshot of every
page for offline review / archival.

Per 2026-09-06 user feedback (visual inspection): the user wants to
see the full state of every page without the daemon running. This
script captures each page at all 6 themes and writes a single
index.html that links to all the snapshots.

Usage:
    python scripts/doc-snapshot.py
    python scripts/doc-snapshot.py --output .meta/snapshots/
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAP_BASE = Path(r"C:\Users\lion_\AppData\Local\Temp\sonic-sounds-smoke\snapshots")

ALL_PAGES = ["albums.html", "studio.html", "intake.html", "library.html",
             "dashboard.html", "album.html", "index.html"]
THEMES = ["mixtape85", "tokyo-night", "catppuccin-latte", "gruvbox-dark",
          "everforest", "kanagawa"]


def main() -> int:
    p = argparse.ArgumentParser(description="snapshot generator")
    p.add_argument("--base", default="http://127.0.0.1:8765")
    p.add_argument("--output", default=str(SNAP_BASE))
    args = p.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright
    pages = []
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        page = browser.contexts[0].pages[0]
        for path in ALL_PAGES:
            for theme in THEMES:
                ts = int(time.time())
                url = f"{args.base}/site/{path}?v=snap-{theme}-{ts}"
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(700)
                page.evaluate(f"window.Themes && window.Themes.set('{theme}')")
                page.wait_for_timeout(400)
                fname = f"{Path(path).stem}__{theme}.png"
                page.screenshot(path=str(out / fname), full_page=False)
                pages.append((path, theme, fname))

    # Build an index.html
    rows = []
    for path in ALL_PAGES:
        cells = []
        for theme in THEMES:
            png = f"{Path(path).stem}__{theme}.png"
            cells.append(f'<td><a href="{png}">{theme}</a></td>')
        rows.append(f'<tr><td><strong>{path}</strong></td>{"".join(cells)}</tr>')
    header_cells = "".join(f"<th>{t}</th>" for t in THEMES)
    html = f"""<!DOCTYPE html>
<html><head><meta charset='utf-8'><title>sonic-sounds snapshot</title>
<style>body{{font-family:system-ui;background:#0a0a0f;color:#fafafa;padding:20px}}
table{{border-collapse:collapse}}td,th{{border:1px solid #333;padding:8px}}
a{{color:#f0c53c}}</style></head><body>
<h1>sonic-sounds snapshot</h1>
<p>{len(ALL_PAGES)} pages x {len(THEMES)} themes = {len(pages)} screenshots</p>
<table><tr><th>page</th>{header_cells}</tr>
{"".join(rows)}
</table></body></html>"""
    (out / "index.html").write_text(html, encoding="utf-8")
    print(f"[doc-snapshot] wrote {len(pages)} screenshots + index.html to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
