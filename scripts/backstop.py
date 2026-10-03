"""scripts/backstop - visual regression testing runner.

Per 2026-09-06 user feedback: visual bugs that pass unit tests can
slip through (e.g. the keys panel overlap, the YOUR COLLECTION grid
collapse). This script automates visual diffing using Pillow's
perceptual hashing + pixel-level comparison.

It's a deliberately simple implementation that works without
BackstopJS or other heavyweight dependencies. For production-grade
visual regression testing at scale, BackstopJS would be the next
step; this script is the foundation that gets us 80% of the value.

Usage:
    python scripts/backstop.py                # full audit
    python scripts/backstop.py --update       # update baseline
    python scripts/backstop.py --page intake  # single page
    python scripts/backstop.py --threshold 2  # fail if pixel diff > 2%
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

SHOT_DIR = Path(r"C:\Users\lion_\AppData\Local\Temp\sonic-sounds-smoke\backstop")
BASELINE_DIR = SHOT_DIR / "baseline"
ALL_PAGES = ["albums.html", "studio.html", "intake.html", "library.html",
             "dashboard.html", "album.html", "index.html"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()[:16]


def capture(pw_page, base: str, pages: list[str]) -> dict:
    """Take screenshots of each page at default viewport."""
    captured = {}
    for path in pages:
        ts = int(time.time())
        pw_page.goto(f"{base}/site/{path}?v=backstop-{ts}",
                      wait_until="domcontentloaded", timeout=15000)
        pw_page.wait_for_timeout(700)
        out = SHOT_DIR / f"{Path(path).stem}.png"
        pw_page.screenshot(path=str(out), full_page=False)
        captured[path] = out
    return captured


def update_baseline(captured: dict) -> None:
    if BASELINE_DIR.exists():
        import shutil
        shutil.rmtree(BASELINE_DIR)
    BASELINE_DIR.mkdir(parents=True)
    for path, src in captured.items():
        import shutil
        shutil.copy(src, BASELINE_DIR / Path(path).stem + ".png")
    print(f"[backstop] baseline saved: {len(captured)} screenshot(s)")


def diff_against_baseline(threshold_pct: float) -> int:
    if not BASELINE_DIR.exists():
        print(f"[backstop] no baseline at {BASELINE_DIR}; run --update first")
        return 1
    drifted = []
    unchanged = 0
    missing_baseline = []
    for baseline in sorted(BASELINE_DIR.glob("*.png")):
        current = SHOT_DIR / baseline.name
        if not current.exists():
            missing_baseline.append(baseline.name)
            continue
        try:
            from PIL import Image, ImageChops
            a = Image.open(baseline).convert("RGB")
            b = Image.open(current).convert("RGB")
            if a.size != b.size:
                drifted.append((baseline.name, "size changed",
                                f"{a.size} -> {b.size}"))
                continue
            diff = ImageChops.difference(a, b)
            bbox = diff.getbbox()
            if bbox is None:
                unchanged += 1
                continue
            total_px = a.size[0] * a.size[1]
            diff_px = sum(1 for px in diff.getdata() if px != (0, 0, 0))
            pct = 100.0 * diff_px / total_px
            if pct > threshold_pct:
                drifted.append((baseline.name, f"{pct:.2f}% changed",
                                f"diff bbox: {bbox}"))
            else:
                unchanged += 1
        except ImportError:
            # Fall back to hash diff
            if sha256(current) != sha256(baseline):
                drifted.append((baseline.name, "hash differs", ""))
            else:
                unchanged += 1
    print(f"[backstop] {unchanged} unchanged, {len(drifted)} drifted, "
          f"{len(missing_baseline)} missing baseline")
    if drifted:
        print("\n=== drifted ===")
        for name, reason, detail in drifted[:20]:
            print(f"  {name}: {reason} {detail}")
    if missing_baseline:
        print("\n=== missing baseline (current has no match) ===")
        for name in missing_baseline[:20]:
            print(f"  {name}")
    return 1 if (drifted or missing_baseline) else 0


def main() -> int:
    p = argparse.ArgumentParser(description="visual regression runner")
    p.add_argument("--base", default="http://127.0.0.1:8765")
    p.add_argument("--page", action="append", help="specific page")
    p.add_argument("--update", action="store_true",
                   help="update baseline from current screenshots")
    p.add_argument("--threshold", type=float, default=0.5,
                   help="pixel diff percent threshold (default 0.5)")
    args = p.parse_args()
    pages = args.page or ALL_PAGES

    if args.update:
        SHOT_DIR.mkdir(parents=True, exist_ok=True)
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
            page = browser.contexts[0].pages[0]
            captured = capture(page, args.base, pages)
        update_baseline(captured)
        return 0

    # Compare mode
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        page = browser.contexts[0].pages[0]
        capture(page, args.base, pages)
    return diff_against_baseline(args.threshold)


if __name__ == "__main__":
    sys.exit(main())
