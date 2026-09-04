"""sweepers/mirror.py — OneDrive mirror (Day 8).

Per plan section Day 8: "sweepers/mirror.py: every hour, walk albums/
for changes, mirror to OneDrive with md5".

Per R7 + R10 (per user's memory: "durable artifacts → mirror to
~/OneDrive/Hermes/... + md5 verify"), the canonical mirror target
is ~/OneDrive/Hermes/Agents/planning/sonic-studio/.

Implementation: walk the local <project>/albums/ tree. For each
file, compute md5 of local AND mirror. If they differ (or mirror
is missing), copy local -> mirror. Files ONLY present in mirror
(deletions) are NOT removed automatically — that's a human
decision (R7).

Mirror verification (byte-match + md5) is the caller's responsibility
per R7 ("After any change to this file, the mirror loop (R7) will
update the OneDrive copy byte-for-byte"). This sweeper just does
the bytes; verification is run_all.py:do_mirror_check or similar.
"""
from __future__ import annotations

import hashlib
import logging
import os
import shutil
from pathlib import Path
from typing import Optional

_log = logging.getLogger("sonic_studio.sweepers.mirror")


def _md5(path: Path) -> str:
    """Compute md5 of a file. Returns hex digest."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_sweep(*,
              source_dir: Path | None = None,
              mirror_dir: Path | None = None) -> dict:
    """Mirror source_dir -> mirror_dir, byte-for-byte where they differ.

    Args:
      source_dir: defaults to <project>/albums/ (the daemon's artifact root).
      mirror_dir: defaults to ~/OneDrive/Hermes/Agents/planning/sonic-studio/
        per R7.

    Returns:
      dict with keys: ok (bool), copied (int), up_to_date (int),
      errors (list[str]), source_dir (str), mirror_dir (str).
    """
    if source_dir is None:
        source_dir = Path(__file__).resolve().parent.parent / "albums"
    if mirror_dir is None:
        mirror_dir = Path.home() / "OneDrive" / "Hermes" / "Agents" / "planning" / "sonic-studio"

    if not source_dir.exists():
        # No artifacts yet — nothing to mirror. Return ok with zero counts.
        return {
            "ok": True,
            "copied": 0,
            "up_to_date": 0,
            "errors": [],
            "source_dir": str(source_dir),
            "mirror_dir": str(mirror_dir),
        }

    mirror_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    up_to_date = 0
    errors: list[str] = []

    for src in source_dir.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(source_dir)
        dst = mirror_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            if dst.exists() and _md5(src) == _md5(dst):
                up_to_date += 1
                continue
            shutil.copy2(src, dst)
            copied += 1
            _log.debug(f"mirrored {rel}")
        except Exception as e:
            errors.append(f"{rel}: {type(e).__name__}: {e}")
            _log.warning(f"mirror failed for {rel}: {e}")

    return {
        "ok": not errors,
        "copied": copied,
        "up_to_date": up_to_date,
        "errors": errors,
        "source_dir": str(source_dir),
        "mirror_dir": str(mirror_dir),
    }
