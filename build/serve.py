"""build/serve.py — Quart ASGI app (Day 3).

Per PLAN-2026-07-28-v3.4 §Day 3:
- serve.py: singleton lock, signal handlers, startup sequence
- http_router.py: dispatch table for Day 3 endpoints

Day 3 implements 5 endpoints:
  /api/health      GET  subsystem status JSON
  /site/*          GET  static files from site/ directory
  /assets/*        GET  static files from assets/ directory
  /api/audio/<id>  GET  audio with HTTP Range support
  /api/albums      GET  list albums (placeholder for Day 4)
  /api/sessions    GET  list sessions (placeholder for Day 4)

Long-term architecture note (Day 3 audit, 2026-08-09):

The Quart test_client `.get()` is async — sync handlers return a
coroutine that never gets awaited. All handlers must be `async def`.
Sync DB calls inside async handlers use `asyncio.to_thread()` (Python 3.9+)
which offloads the synchronous sqlite3 call to a thread pool. This is the
correct long-term pattern: sqlite3 is sync-only, but Quart is async-only.

The same `create_app()` factory is used in production (hypercorn) and
tests (test_client). This eliminates all subprocess-based test races.
"""
import argparse
import json
import logging
import os
import signal
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from quart import Quart, jsonify, send_file, request, abort

# Project imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db, run_migrations, close_db, DEFAULT_DB_PATH
from db.queries import global_status
from build.singleton import SingletonLock, SingletonLockError
from build.signals import (
    install_signal_handlers, is_shutdown_requested,
    request_shutdown, DEFAULT_SHUTDOWN_SIGNALS,
)

_log = logging.getLogger("album_studio.daemon")

# Project paths
PROJ_ROOT = Path(__file__).parent.parent
SITE_DIR = PROJ_ROOT / "site"
ASSETS_DIR = PROJ_ROOT / "assets"
DEFAULT_LOCK = PROJ_ROOT / ".meta" / "daemon.lock"
DEFAULT_LOG = PROJ_ROOT / ".meta" / "daemon.log"


def create_app() -> Quart:
    """Quart app factory.

    Returns a Quart app configured with all Day 3 routes.
    Used in both production (hypercorn) and testing (QuartClient).
    """
    app = Quart(__name__)
    app.config["PROJ_ROOT"] = PROJ_ROOT
    app.config["SITE_DIR"] = SITE_DIR
    app.config["ASSETS_DIR"] = ASSETS_DIR
    register_routes(app)
    return app


async def _run_in_thread(fn, *args, **kwargs):
    """Run a sync function in a thread (Python 3.9+ asyncio.to_thread)."""
    import asyncio
    return await asyncio.to_thread(fn, *args, **kwargs)


def register_routes(app: Quart) -> None:
    """Register all Day 3 routes on the Quart app."""

    @app.route("/api/health", methods=["GET"])
    async def health():
        """Health endpoint with subsystem status."""
        status = await _run_in_thread(global_status)
        payload = {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "subsystems": {
                "db": "ok",
                "http": "ok",
                "static": "ok",
                "audio": "ok (range support)",
                "build_runner": "not yet (Day 6)",
                "sweepers": "not yet (Day 8)",
            },
            "counts": status,
        }
        return jsonify(payload)

    @app.route("/site/<path:filepath>", methods=["GET"])
    async def site_static(filepath: str):
        """Static file handler for site/ directory."""
        target = (SITE_DIR / filepath).resolve()
        try:
            target.relative_to(SITE_DIR.resolve())
        except ValueError:
            abort(403)
        if not target.is_file():
            abort(404)
        return await send_file(str(target))

    @app.route("/assets/<path:filepath>", methods=["GET"])
    async def assets_static(filepath: str):
        """Static file handler for assets/ directory."""
        target = (ASSETS_DIR / filepath).resolve()
        try:
            target.relative_to(ASSETS_DIR.resolve())
        except ValueError:
            abort(403)
        if not target.is_file():
            abort(404)
        return await send_file(str(target))

    @app.route("/api/audio/<track_id>", methods=["GET"])
    async def audio_range(track_id: str):
        """Audio handler with HTTP Range support (per Day 3 plan).

        Streams the MP3 file with proper Range request handling so audio
        scrubbing works in browsers.
        """
        def _lookup():
            conn = open_db()
            try:
                row = conn.execute(
                    "SELECT mp3_path, duration_sec FROM tracks WHERE id = ?",
                    (track_id,)
                ).fetchone()
                if row:
                    return {"mp3_path": row["mp3_path"], "duration_sec": row["duration_sec"]}
                return None
            finally:
                conn.close()

        track = await _run_in_thread(_lookup)
        if not track or not track.get("mp3_path"):
            abort(404)

        mp3_rel = track["mp3_path"]
        candidates = [
            PROJ_ROOT / mp3_rel,
            PROJ_ROOT / "music" / Path(mp3_rel).name,
        ]
        target = None
        for c in candidates:
            if c.exists() and c.is_file():
                target = c
                break
        if target is None:
            abort(404)

        return await send_file(str(target), conditional=True, mimetype="audio/mpeg")

    # === Day 4+ placeholders (will be wired in Day 4-5) ===

    @app.route("/api/albums", methods=["GET"])
    async def list_albums():
        """List albums (placeholder, Day 4 will add filters)."""
        from db.albums import list_albums as db_list_albums
        result = await _run_in_thread(db_list_albums)
        return jsonify(result)

    @app.route("/api/sessions", methods=["GET"])
    async def list_sessions():
        """List sessions (placeholder, Day 4 will add filters)."""
        from db.sessions import list_sessions as db_list_sessions
        result = await _run_in_thread(db_list_sessions)
        return jsonify(result)


# === Daemon lifecycle ===

class Daemon:
    """The album-studio daemon.

    Lifecycle:
      1. Acquire singleton lock
      2. Initialize logging
      3. Run pending migrations
      4. Install signal handlers
      5. Start ASGI server (blocks until shutdown signal)
      6. Cleanup
    """

    def __init__(self,
                 host: str = "127.0.0.1",
                 port: int = 8765,
                 lock_path: Optional[Path] = None,
                 log_path: Optional[Path] = None):
        self.host = host
        self.port = port
        self.lock_path = lock_path or DEFAULT_LOCK
        self.log_path = log_path or DEFAULT_LOG
        self.lock = SingletonLock(self.lock_path)

    def setup_logging(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(str(self.log_path), mode="a"),
            ],
        )

    def acquire_lock(self) -> None:
        try:
            self.lock.acquire()
        except SingletonLockError as e:
            _log.error(f"Cannot start daemon: {e}")
            sys.exit(1)
        _log.info(f"acquired singleton lock at {self.lock_path}")

    def install_signal_handlers(self) -> None:
        install_signal_handlers()
        _log.info(f"installed signal handlers for {DEFAULT_SHUTDOWN_SIGNALS}")

    def run_migrations(self) -> None:
        result = run_migrations()
        if result["errors"]:
            _log.error(f"migration errors: {result['errors']}")
            sys.exit(1)
        _log.info(f"migrations applied (schema_version={result['schema_version']})")

    def start(self) -> None:
        """Start the daemon (blocking until shutdown signal)."""
        self.setup_logging()
        self.acquire_lock()
        self.run_migrations()
        self.install_signal_handlers()

        app = create_app()
        _log.info(f"starting on {self.host}:{self.port}")

        import asyncio
        from hypercorn.config import Config
        from hypercorn.asyncio import serve as hypercorn_serve

        config = Config()
        config.bind = [f"{self.host}:{self.port}"]
        config.graceful_timeout = 2.0

        try:
            asyncio.run(hypercorn_serve(app, config))
        except KeyboardInterrupt:
            pass
        finally:
            _log.info("shutting down")
            self.lock.release()
            close_db()


# === CLI entry point ===

def main() -> int:
    parser = argparse.ArgumentParser(description="album-studio daemon")
    parser.add_argument("--host", default="127.0.0.1", help="bind host")
    parser.add_argument("--port", type=int, default=8765, help="bind port")
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK, help="singleton lock path")
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG, help="daemon log path")
    args = parser.parse_args()

    daemon = Daemon(host=args.host, port=args.port,
                    lock_path=args.lock, log_path=args.log)
    daemon.start()
    return 0


if __name__ == "__main__":
    sys.exit(main())
