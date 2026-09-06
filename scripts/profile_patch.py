"""Request-profiler middleware for the daemon (used by scripts/profile.py).

This is a standalone module so it can be loaded by build/serve.py
without changing that file's import surface. Set
SONIC_SOUNDS_PROFILE=1 in the daemon's environment to enable it.

What it does:
  - Before each request: record start time
  - After each request: record route, method, status, duration
  - Flush to .meta/profile.json on shutdown

Note: this is read by scripts/profile.py and stays out of the
hot path. It's a tiny overhead (~5us per request) so it's safe to
enable in dev.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

ENABLED = os.environ.get("SONIC_SOUNDS_PROFILE") == "1"
PROFILE_PATH = Path(__file__).resolve().parent.parent / ".meta" / "profile.json"

_samples: list[dict] = []


def reset() -> None:
    """Clear collected samples (useful for tests)."""
    _samples.clear()
    if PROFILE_PATH.exists():
        PROFILE_PATH.unlink()


def record(method: str, path: str, status: int, duration_ms: float) -> None:
    _samples.append({
        "method": method,
        "route": path,
        "status": status,
        "duration_ms": duration_ms,
        "ts": time.time(),
    })


def flush() -> None:
    if not _samples:
        return
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {"samples": list(_samples)}
    if PROFILE_PATH.exists():
        # Merge with existing data so we don't lose samples on flush
        try:
            existing = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
            data["samples"] = existing.get("samples", []) + _samples
        except Exception:
            pass
    PROFILE_PATH.write_text(json.dumps(data), encoding="utf-8")
    _samples.clear()


def install(app):
    """Install before/after request hooks on a Quart app."""
    if not ENABLED:
        return
    from time import perf_counter
    @app.before_request
    def _start():
        from flask import request as _req
        _req.environ["_ss_profile_start"] = perf_counter()
    @app.after_request
    def _stop(response):
        from flask import request as _req
        start = _req.environ.get("_ss_profile_start")
        if start is None:
            return response
        dur_ms = (perf_counter() - start) * 1000
        # Route is the URL rule (or the raw path if no rule)
        from flask import request as _req2
        rule = _req2.url_rule.rule if _req2.url_rule else _req2.path
        record(_req2.method, rule, response.status_code, dur_ms)
        return response
    import atexit
    atexit.register(flush)
    return app
