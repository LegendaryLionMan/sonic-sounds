"""sweepers/wal_checkpoint.py — periodic WAL truncation (Day 8).

Per plan section Day 8: "sweepers/wal_checkpoint.py: every 15 min,
PRAGMA wal_checkpoint(TRUNCATE)".

This bounds the WAL file size. Without it, the WAL grows on every
write and only truncates on a passive checkpoint. For a daemon that
writes infrequently, the WAL can grow to many MB without ever
truncating. The TRUNCATE mode truncates the WAL back to zero length
after checkpointing.

Implementation note: wal_checkpoint() runs against every open
connection's db file. The per-thread connection cache in db.connection
caches one conn per thread per db_path. The sweeper runs on a single
daemon thread, so it has exactly one conn. PRAGMA wal_checkpoint on
that conn truncates the WAL.
"""
from __future__ import annotations

import logging

from db.connection import open_db, close_db

_log = logging.getLogger("album_studio.sweepers.wal_checkpoint")


def run_sweep(*, mode: str = "TRUNCATE") -> dict:
    """Run PRAGMA wal_checkpoint(MODE).

    Args:
      mode: 'PASSIVE' | 'FULL' | 'RESTART' | 'TRUNCATE'. Default TRUNCATE
        per plan; truncate aggressively bounds WAL size.

    Returns:
      dict with keys: busy (int frames still busy), log (int frames in WAL),
      checkpointed (int frames checkpointed), mode (str).
    """
    if mode not in ("PASSIVE", "FULL", "RESTART", "TRUNCATE"):
        raise ValueError(f"invalid wal_checkpoint mode: {mode!r}")
    conn = open_db()
    try:
        cur = conn.execute(f"PRAGMA wal_checkpoint({mode})")
        row = cur.fetchone()
        # Row shape: (busy, log, checkpointed)
        # Per https://www.sqlite.org/wal.html#wal_checkpoint
        # Note: pragmas with multiple return values come back as a tuple.
        busy = row[0] if row else 0
        log_size = row[1] if row else 0
        checkpointed = row[2] if row else 0
        _log.info(f"WAL checkpoint ({mode}): busy={busy} log={log_size} checkpointed={checkpointed}")
        return {
            "busy": busy,
            "log": log_size,
            "checkpointed": checkpointed,
            "mode": mode,
        }
    finally:
        close_db()
