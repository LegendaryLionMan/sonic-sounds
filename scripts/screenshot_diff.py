"""scripts/screenshot-diff - visual regression detector for the e2e suite.

Usage:
    python scripts/screenshot-diff                # diff current vs baseline
    python scripts/screenshot-diff --update      # update baseline from current
    python scripts/screenshot-diff --threshold 2  # fail if pixel diff > 2%

The e2e visual suite saves 42 PNGs to
C:/Users/lion_/AppData/Local/Temp/sonic-sounds-smoke/e2e-advanced/.
This script:
  - On first run: --update copies current to a baseline dir
  - On later runs: compares every PNG to the baseline pixel-by-pixel
    using PIL.ImageChops.difference. Reports any with non-zero diff.

Designed to catch unintended visual regressions (e.g. someone changes
a CSS rule and accidentally breaks the cassette aspect ratio).
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

SHOT_DIR = Path(r"C:\Users\lion_\AppData\Local\Temp\sonic-sounds-smoke\e2e-advanced")
BASELINE_DIR = SHOT_DIR / "baseline"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()[:16]


def update_baseline() -> None:
    if BASELINE_DIR.exists():
        shutil.rmtree(BASELINE_DIR)
    BASELINE_DIR.mkdir(parents=True)
    count = 0
    for p in SHOT_DIR.glob("*.png"):
        shutil.copy(p, BASELINE_DIR / p.name)
        count += 1
    print(f"[diff] baseline updated: {count} screenshot(s)")


def diff_baseline(threshold_pct: float) -> int:
    if not BASELINE_DIR.exists():
        print(f"[diff] no baseline at {BASELINE_DIR}")
        print("       run with --update first")
        return 1
    try:
        from PIL import Image, ImageChops
    except ImportError:
        print("[diff] Pillow not installed; falling back to hash comparison")
        return diff_baseline_by_hash()
    drifted = []
    unchanged = 0
    missing = []
    for baseline in sorted(BASELINE_DIR.glob("*.png")):
        current = SHOT_DIR / baseline.name
        if not current.exists():
            missing.append(baseline.name)
            continue
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
        # Compute percent of pixels that changed
        total_px = a.size[0] * a.size[1]
        diff_px = sum(1 for px in diff.getdata() if px != (0, 0, 0))
        pct = 100.0 * diff_px / total_px
        if pct > threshold_pct:
            drifted.append((baseline.name, "pixel diff", f"{pct:.2f}% changed"))
        else:
            unchanged += 1
    print(f"[diff] {unchanged} unchanged, {len(drifted)} drifted, "
          f"{len(missing)} missing")
    if drifted:
        print("\n=== drifted (> {:.1f}% pixels) ===".format(threshold_pct))
        for name, reason, detail in drifted[:20]:
            print(f"  {name}  ({reason}: {detail})")
    if missing:
        print("\n=== missing (in current but expected from baseline) ===")
        for name in missing[:20]:
            print(f"  {name}")
    return 1 if (drifted or missing) else 0


def diff_baseline_by_hash() -> int:
    """Hash-based diff for environments without Pillow."""
    drifted = []
    unchanged = 0
    missing = []
    for baseline in sorted(BASELINE_DIR.glob("*.png")):
        current = SHOT_DIR / baseline.name
        if not current.exists():
            missing.append(baseline.name)
            continue
        if sha256(current) == sha256(baseline):
            unchanged += 1
        else:
            drifted.append(baseline.name)
    print(f"[diff] {unchanged} unchanged, {len(drifted)} drifted, "
          f"{len(missing)} missing")
    if drifted:
        print("\n=== drifted (hash differs) ===")
        for name in drifted[:20]:
            print(f"  {name}")
    if missing:
        print("\n=== missing ===")
        for name in missing[:20]:
            print(f"  {name}")
    return 1 if (drifted or missing) else 0


def main() -> int:
    p = argparse.ArgumentParser(description="screenshot regression diff")
    p.add_argument("--update", action="store_true",
                   help="update baseline from current screenshots")
    p.add_argument("--threshold", type=float, default=0.5,
                   help="pixel diff percent threshold (default 0.5)")
    args = p.parse_args()
    if args.update:
        update_baseline()
        return 0
    return diff_baseline(args.threshold)


if __name__ == "__main__":
    sys.exit(main())
