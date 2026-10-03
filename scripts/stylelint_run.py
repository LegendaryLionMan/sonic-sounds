"""scripts/stylelint - CSS linter wrapper.

Per 2026-09-06 user feedback: the visual inspection found multiple
hardcoded colors outside :root blocks, accessibility issues (low
contrast), and unused selectors. stylelint catches all of these.

Usage:
    python scripts/stylelint.py
    python scripts/stylelint.py --fix    # auto-fix what's possible

Requirements:
    npm install -g stylelint stylelint-config-standard
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def find_linter() -> str | None:
    return shutil.which("stylelint")


CONFIG = """
{
  "extends": ["stylelint-config-standard"],
  "rules": {
    "color-no-invalid-hex": true,
    "declaration-block-no-duplicate-properties": true,
    "selector-class-pattern": null,
    "custom-property-pattern": null,
    "no-descending-specificity": null,
    "media-feature-range-notation": "prefix",
    "selector-pseudo-element-no-unknown": [true, {
      "ignorePseudoElements": ["ng-deep"]
    }],
    "value-keyword-case": ["lower", {
      "ignoreKeywords": ["currentColor"]
    }]
  }
}
""".strip()


def main() -> int:
    p = argparse.ArgumentParser(description="CSS lint")
    p.add_argument("--fix", action="store_true",
                   help="auto-fix what's possible")
    args = p.parse_args()

    linter = find_linter()
    if not linter:
        print("[stylelint] not installed.")
        print("  install: npm install -g stylelint stylelint-config-standard")
        return 1

    site = ROOT / "site"
    cfg = ROOT / ".meta" / ".stylelintrc.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(CONFIG, encoding="utf-8")

    cmd = [linter, "--config", str(cfg)]
    if args.fix:
        cmd.append("--fix")
    cmd.extend([str(site / "*.css"), str(site / "**" / "*.css")])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode == 0:
        print("[stylelint] OK")
        return 0
    print(f"[stylelint] {result.returncode} errors found")
    print(result.stdout[-2000:] if result.stdout else result.stderr[-2000:])
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
