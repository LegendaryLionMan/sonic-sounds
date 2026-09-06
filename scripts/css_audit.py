"""scripts/css-audit - scan CSS files for hardcoded colors that bypass theme tokens.

Usage:
    python scripts/css-audit                # scan all .css files
    python scripts/css-audit --strict       # fail on any hardcoded color
    python scripts/css-audit --file path    # scan specific file

A theme-aware site should use the CSS custom properties (--bg, --ink,
--accent, --rule, etc.) instead of literal hex/rgb/hsl values in
component-level rules. Literal colors are sometimes necessary (for
gradients, shadows, decorative effects), but the audit flags them so
a human can review.

The audit:
  - parses each CSS file
  - distinguishes "good" colors (in :root or :root[data-theme=...] blocks)
    from "bad" colors (everywhere else)
  - ignores rgba(0,0,0,X) and rgba(255,255,255,X) alpha shadows
  - prints a per-file summary with line numbers
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = ROOT / "site"

# Patterns for finding color literals
COLOR_PATTERNS = [
    re.compile(r"#[0-9a-fA-F]{3,8}\b"),  # hex
    re.compile(r"\brgba?\(\s*\d"),           # rgb/rgba
    re.compile(r"\bhsla?\(\s*\d"),          # hsl/hsla
]


def is_alpha_black_white(text: str) -> bool:
    """Skip pure alpha-channel colors (rgba(0,0,0,X) and rgba(255,255,255,X))
    that are commonly used as shadows / overlays — not 'real' colors."""
    m = re.search(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,", text)
    if not m:
        return False
    r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
    # Acceptable shadow tints
    return (r, g, b) in [(0, 0, 0), (255, 255, 255)]


def is_in_root_block(text: str, line_no: int, block_ranges: list[tuple[int, int]]) -> bool:
    """Was this line inside a :root or :root[data-theme=...] block?"""
    for start, end in block_ranges:
        if start <= line_no <= end:
            return True
    return False


def find_root_block_ranges(lines: list[str]) -> list[tuple[int, int]]:
    """Find line ranges of :root, :root[data-theme=...], and :root:not(...) blocks."""
    ranges = []
    open_idx = None
    brace_depth = 0
    # Match any :root selector with optional [attr], :not(), or pseudo
    root_open_re = re.compile(r"^:root\b[^\{]*\{")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if open_idx is None:
            if root_open_re.match(stripped):
                open_idx = i
                brace_depth = stripped.count("{") - stripped.count("}")
                if brace_depth == 0:
                    ranges.append((i, i))
                    open_idx = None
        else:
            brace_depth += line.count("{") - line.count("}")
            if brace_depth <= 0:
                ranges.append((open_idx, i))
                open_idx = None
    return ranges


def audit_file(path: Path) -> list[tuple[int, str, str]]:
    """Return list of (line_no, color, context) for hardcoded colors."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    root_ranges = find_root_block_ranges(lines)
    findings = []
    for i, line in enumerate(lines, start=1):
        if is_in_root_block(text, i, root_ranges):
            continue  # :root blocks are allowed to have literal colors
        for pat in COLOR_PATTERNS:
            for m in pat.finditer(line):
                color = m.group(0)
                if is_alpha_black_white(color):
                    continue
                # Skip common false positives
                if "/*" in line and line.find("/*") < m.start():
                    continue  # in a comment
                findings.append((i, color, line.strip()[:80]))
    return findings


def main() -> int:
    p = argparse.ArgumentParser(description="CSS color audit")
    p.add_argument("--file", type=Path, help="audit a single file")
    p.add_argument("--strict", action="store_true",
                   help="exit non-zero if any hardcoded color found")
    p.add_argument("--quiet", action="store_true",
                   help="only print files WITH findings")
    args = p.parse_args()

    if args.file:
        targets = [args.file]
    else:
        targets = sorted(SITE_DIR.glob("*.css"))

    total_findings = 0
    files_with_findings = 0
    for path in targets:
        findings = audit_file(path)
        if findings:
            files_with_findings += 1
            total_findings += len(findings)
            print(f"\n{path.name}: {len(findings)} hardcoded color(s) outside :root blocks")
            if not args.quiet or findings:
                for line_no, color, ctx in findings[:20]:
                    print(f"  L{line_no:4d}  {color:20s}  {ctx}")
                if len(findings) > 20:
                    print(f"  ...and {len(findings) - 20} more")
        else:
            if not args.quiet:
                # Only print clean files in non-quiet mode
                pass

    print(f"\n=== summary: {files_with_findings} file(s) with findings, "
          f"{total_findings} total ===")

    if args.strict and total_findings > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
