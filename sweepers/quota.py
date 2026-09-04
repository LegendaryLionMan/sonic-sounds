"""sweepers/quota.py — periodic quota snapshot (Day 8).

Per plan section Day 8: "sweepers/quota.py: every 5 min, call
mmx_quota_show, write to quota_snapshots".

The quota_snapshots table is defined in db/schema.sql (Day 2).
We use MCP tool mmx_quota_show when available; fall back to a
direct CLI call if MCP isn't reachable. Per user's mmx memory:
"Quota: MCP mmx_quota_show before batch work".

The schema for quota_snapshots is:
  created_at      TEXT NOT NULL DEFAULT (datetime('now')),
  general_pct     INTEGER,
  video_pct       INTEGER,
  audio_pct       INTEGER,
  interval_remains_ms INTEGER,
  raw_json        TEXT

This matches the response shape of /api/health's "quota_remaining"
key, which comes from mmx_quota_show per the daemon's health check.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_log = logging.getLogger("sonic_studio.sweepers.quota")


def _read_quota_via_mcp() -> Optional[dict]:
    """Try MCP mmx_quota_show first (per memory: 'Quota: MCP mmx_quota_show').

    Returns the parsed quota dict on success; None on failure.
    """
    try:
        # Lazy import: don't hard-fail the sweeper if MCP isn't installed.
        from mmx_cli import quota_show  # type: ignore
        return quota_show()
    except Exception as e:
        _log.debug(f"MCP mmx_quota_show unavailable: {e}")
        return None


def _read_quota_via_cli() -> Optional[dict]:
    """Fallback: run mmx quota show and parse stdout."""
    mmx = os.environ.get("SONIC_STUDIO_MMX_CMD") or r"C:\Users\lion_\AppData\Roaming\npm\mmx.cmd"
    try:
        result = subprocess.run(
            [mmx, "quota", "show"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            _log.warning(f"mmx quota show rc={result.returncode}: {result.stderr[:200]}")
            return None
        return json.loads(result.stdout)
    except Exception as e:
        _log.debug(f"mmx quota show via CLI unavailable: {e}")
        return None


def read_quota() -> Optional[dict]:
    """Read current quota. Try MCP first, fall back to CLI."""
    return _read_quota_via_mcp() or _read_quota_via_cli()


def _open_db():
    from db.connection import open_db
    return open_db()


def _close_db():
    from db.connection import close_db
    close_db()


def run_sweep() -> dict:
    """Snapshot current quota and persist to quota_snapshots.

    Returns:
      dict with keys: ok (bool), general_pct (int|None), video_pct (int|None),
      audio_pct (int|None), interval_remains_ms (int|None), error (str|None).
    """
    quota = read_quota()
    if quota is None:
        return {"ok": False, "error": "quota source unavailable (MCP + CLI both failed)"}

    # Normalize the dict. Different mmx versions return different shapes;
    # be defensive.
    general_pct = quota.get("general_pct") or quota.get("general") or quota.get("general_remaining_pct")
    video_pct = quota.get("video_pct") or quota.get("video") or quota.get("video_remaining_pct")
    audio_pct = quota.get("audio_pct") or quota.get("audio") or quota.get("audio_remaining_pct")
    interval_remains_ms = quota.get("interval_remains_ms") or quota.get("interval_remains") or 0

    try:
        from db import connection as db_conn
        # Schema is one-row-per-(model_kind, snapshot). Insert 3 rows
        # for general/video/speech (audio → 'speech' in legacy mmx naming).
        conn = db_conn.open_db()
        try:
            rows = [
                ("general", general_pct),
                ("video",   video_pct),
                ("speech",  audio_pct),
            ]
            for model_kind, interval_pct in rows:
                if interval_pct is None:
                    continue
                conn.execute(
                    """INSERT INTO quota_snapshots
                           (model_kind, interval_pct, interval_remaining_ms)
                       VALUES (?, ?, ?)""",
                    (model_kind, float(interval_pct), interval_remains_ms),
                )
            conn.commit()
        finally:
            db_conn.close_db()
        _log.info(f"quota snapshot: general={general_pct} video={video_pct} audio={audio_pct} interval_ms={interval_remains_ms}")
        return {
            "ok": True,
            "general_pct": general_pct,
            "video_pct": video_pct,
            "audio_pct": audio_pct,
            "interval_remains_ms": interval_remains_ms,
        }
    except Exception as e:
        _log.exception("quota snapshot insert failed")
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
