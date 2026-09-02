"""sweepers/idle_pause.py — auto-pause sessions idle for 12+ hours (Day 8).

Per plan section Day 8: "sweepers/idle_pause.py: every 5 min, mark
active sessions with last_activity_at < now-12h as paused".

The 12-hour threshold is the Q32 value (db/sessions.py:IDLE_THRESHOLD_HOURS).
Reuse db/sessions.idle_hours and db/sessions.pause_session to avoid
duplicate logic.

Usage:
    from sweepers import idle_pause
    result = idle_pause.run_sweep()
    # {'candidates': N, 'paused': M, 'errors': [...]}

The daemon's startup sequence registers this sweeper as a daemon
thread (see build/serve.py:start_sweepers).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import db.sessions as db_sessions

_log = logging.getLogger("album_studio.sweepers.idle_pause")


def run_sweep(*, threshold_hours: Optional[float] = None,
              now_iso: Optional[str] = None) -> dict:
    """Find active sessions idle for >= threshold_hours and pause them.

    Args:
      threshold_hours: override the Q32 default (12h). For tests.
      now_iso: override the wall clock. For tests.

    Returns:
      dict with keys: candidates (int), paused (int), paused_ids (list[str]),
      errors (list[str]).
    """
    threshold = threshold_hours if threshold_hours is not None else db_sessions.IDLE_THRESHOLD_HOURS

    # Enumerate active sessions and check each one's idle_hours
    sessions = db_sessions.list_sessions(status="active")
    paused_ids: list[str] = []
    errors: list[str] = []

    for sess in sessions:
        sid = sess["id"]
        try:
            idle = db_sessions.idle_hours(sid)
            if idle is None:
                # Session vanished between list and idle check — skip
                continue
            if idle >= threshold:
                db_sessions.pause_session(sid)
                paused_ids.append(sid)
                _log.info(f"auto-paused session {sid[:8]} (idle {idle:.1f}h >= {threshold}h)")
        except Exception as e:
            errors.append(f"{sid}: {type(e).__name__}: {e}")
            _log.exception(f"failed to pause session {sid}")

    return {
        "candidates": len(sessions),
        "paused": len(paused_ids),
        "paused_ids": paused_ids,
        "errors": errors,
    }
