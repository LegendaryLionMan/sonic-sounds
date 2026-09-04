"""scripts/verify-mirror.py - OneDrive mirror byte-match verification (Day 12).

Per plan section Day 12:
  "OneDrive mirror: verify .db byte-matches OneDrive copy"
Per user's R7/R10 (memory):
  "durable artifacts -> mirror to ~/OneDrive/Hermes/... + md5 verify"

This script walks <project_root>/albums/ AND <project_root>/.meta/ and
verifies that the files exist in the OneDrive mirror with matching
md5. Exits non-zero on any mismatch.

Usage:
  python scripts/verify-mirror.py [--base <project_root>] [--mirror <one_dir>]

Public API:
  verify_mirror(base_dir, mirror_dir) -> dict
    Returns {ok, files_checked, matched, mismatches, errors, missing}
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Union

_log = logging.getLogger("sonic_sounds.scripts.verify_mirror")


def _md5(path: Path) -> str:
    """Compute md5 hex digest of a file (read in 64KB chunks)."""
    h = hashlib.md5()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(64 * 1024), b""):
                h.update(chunk)
    except OSError as e:
        return f"<unreadable: {e}>"
    return h.hexdigest()


def verify_mirror(base_dir: Union[str, Path],
                 mirror_dir: Union[str, Path],
                 *,
                 include_meta: bool = True) -> dict:
    """Walk base_dir/albums/ (+ optionally .meta/) and verify mirror.

    Returns a summary dict suitable for jsonify/print:
      {
        ok: bool,             # True if no mismatches/missing/errors
        files_checked: int,
        matched: int,
        mismatches: [{rel, src_md5, dst_md5, reason}],
        missing: [{rel, in: 'src' | 'dst'}],
        errors: [str],
        base_dir: str,
        mirror_dir: str,
      }
    """
    base = Path(base_dir).resolve()
    mirror = Path(mirror_dir).resolve()

    if not base.exists():
        return {
            "ok": False,
            "error": f"base_dir does not exist: {base}",
            "base_dir": str(base),
            "mirror_dir": str(mirror),
        }

    summary = {
        "ok": True,
        "files_checked": 0,
        "matched": 0,
        "mismatches": [],
        "missing": [],
        "errors": [],
        "base_dir": str(base),
        "mirror_dir": str(mirror),
    }

    # Walk: albums/ is the main artifact tree
    subdirs = ["albums"]
    if include_meta:
        subdirs.append(".meta")

    for sub in subdirs:
        src_root = base / sub
        if not src_root.exists():
            continue
        for src in src_root.rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(base)
            dst = mirror / rel
            summary["files_checked"] += 1
            if not dst.exists():
                summary["missing"].append({"rel": str(rel), "in": "dst"})
                summary["ok"] = False
                continue
            try:
                src_md5 = _md5(src)
                dst_md5 = _md5(dst)
            except Exception as e:
                summary["errors"].append(f"{rel}: {e}")
                summary["ok"] = False
                continue
            if src_md5 != dst_md5:
                summary["mismatches"].append({
                    "rel": str(rel),
                    "src_md5": src_md5,
                    "dst_md5": dst_md5,
                })
                summary["ok"] = False
            else:
                summary["matched"] += 1

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify OneDrive mirror byte-matches the project albums/ tree."
    )
    parser.add_argument("--base", default=".",
                        help="Project root (default: current directory)")
    parser.add_argument("--mirror", default=None,
                        help="OneDrive mirror path (default: ~/OneDrive/Hermes/Agents/planning/sonic-sounds)")
    parser.add_argument("--no-meta", action="store_true",
                        help="Skip .meta/ subdirectory (only check albums/)")
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON instead of human summary")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    if args.mirror is None:
        # Per R7: OneDrive/Hermes/Agents/planning/<project-name>/
        mirror = Path.home() / "OneDrive" / "Hermes" / "Agents" / "planning" / "sonic-sounds"
    else:
        mirror = Path(args.mirror)

    summary = verify_mirror(args.base, mirror, include_meta=not args.no_meta)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        if summary["ok"]:
            print(f"✅ Mirror OK ({summary['matched']}/{summary['files_checked']} files matched)")
        else:
            print(f"❌ Mirror MISMATCH ({summary['matched']} matched, {len(summary['mismatches'])} mismatched, {len(summary['missing'])} missing, {len(summary['errors'])} errors)")
        if summary.get("error"):
            print(f"  error: {summary['error']}")
        for m in summary["mismatches"][:10]:
            print(f"  MISMATCH: {m['rel']}")
        for m in summary["missing"][:10]:
            print(f"  MISSING in {m['in']}: {m['rel']}")
        for e in summary["errors"][:10]:
            print(f"  ERROR: {e}")

    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
