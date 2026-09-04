"""sweepers/log_rotate.py — daemon log rotation (Day 8).

Per plan section Day 8: "sweepers/log_rotate.py: rotate
.meta/daemon.log daily or at 10MB".

Simple size-based rotation: when the log file exceeds max_bytes,
rename to .1 (overwriting any existing .1) and the daemon's next
write creates a fresh file. We don't use Python's logging.handlers
.RotatingFileHandler because the daemon configures logging via
logging.basicConfig elsewhere; this sweeper does the rotate.

Threshold: 10MB default. Daily rotation is handled separately
(sweepers can call this every minute; the size check decides).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

_log = logging.getLogger("sonic_sounds.sweepers.log_rotate")


def run_sweep(*, log_path: Path | None = None,
              max_bytes: int = 10 * 1024 * 1024) -> dict:
    """Rotate log_path if it exceeds max_bytes.

    Args:
      log_path: defaults to .meta/daemon.log (Q25/R10 canonical location).
      max_bytes: rotation threshold (default 10 MB).

    Returns:
      dict with keys: rotated (bool), size_before (int|None),
      log_path (str), backup_path (str|None).
    """
    if log_path is None:
        # Canonical path per Q25: .meta/daemon.log inside project root.
        log_path = Path(__file__).resolve().parent.parent / ".meta" / "daemon.log"

    if not log_path.exists():
        return {"rotated": False, "size_before": None, "log_path": str(log_path), "backup_path": None}

    size = log_path.stat().st_size
    if size < max_bytes:
        return {"rotated": False, "size_before": size, "log_path": str(log_path), "backup_path": None}

    backup = log_path.with_suffix(log_path.suffix + ".1")
    # If backup exists, just delete it (we keep one generation only).
    # Naming pattern: daemon.log / daemon.log.1
    if backup.exists():
        backup.unlink()
    log_path.rename(backup)
    _log.info(f"rotated {log_path} ({size} bytes) -> {backup}")
    return {
        "rotated": True,
        "size_before": size,
        "log_path": str(log_path),
        "backup_path": str(backup),
    }
