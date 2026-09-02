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
# Note: we intentionally do NOT bind db.* names at module top-level here.
# When tests delete+reimport db.* modules to reset DEFAULT_DB_PATH for
# per-class tempdbs, top-level bindings like `from db import open_db`
# would freeze on the FIRST import's function objects (whose __globals__
# point at the OLD module instance with the wrong DEFAULT_DB_PATH).
# Instead we do local imports of db.connection inside each handler/route
# closure so the call always sees the current sys.modules["db.connection"].
from db.queries import global_status
from build.singleton import SingletonLock, SingletonLockError
from build.signals import (
    install_signal_handlers, is_shutdown_requested,
    request_shutdown, DEFAULT_SHUTDOWN_SIGNALS,
)
# Day 4: split handlers into their own modules so each set of routes
# has a single home (albums vs sessions). The Blueprints are registered
# via register_routes() below.
from build.handlers_albums import albums_bp
from build.handlers_sessions import sessions_bp
from build.handlers_events import events_bp
from build.handlers_decisions import decisions_bp
from build.handlers_build import build_bp
from build.handlers_intake import intake_bp

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


def _build_runner_loaded() -> bool:
    """Day 6 build runner is wired and importable."""
    try:
        import build.runner  # noqa: F401
        return True
    except Exception:
        return False


def _sweepers_loaded() -> bool:
    """Day 8 sweepers module is importable."""
    try:
        import sweepers  # noqa: F401
        return True
    except Exception:
        return False


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
                "build_runner": "ok" if _build_runner_loaded() else "not yet (Day 6)",
                "sweepers": "ok" if _sweepers_loaded() else "not yet (Day 8)",
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
        # Local import so per-test tempdb isolation (which re-imports db.*
        # modules) is honored — a top-level `from db import open_db`
        # would freeze on the FIRST import's function object whose
        # __globals__ reference the wrong module instance.
        from db.connection import open_db, close_db
        def _lookup():
            conn = open_db()
            try:
                row = conn.execute(
                    "SELECT t.mp3_path, t.duration_sec, t.album_id "
                    "FROM tracks t WHERE t.id = ?",
                    (track_id,),
                ).fetchone()
                if row:
                    return {"mp3_path": row["mp3_path"],
                            "duration_sec": row["duration_sec"],
                            "album_id": row["album_id"]}
                return None
            finally:
                # Use close_db() so the per-thread connection cache is
                # popped, not just closed. Otherwise the next open_db() in
                # this thread would return a closed connection from cache.
                close_db()

        track = await _run_in_thread(_lookup)
        if not track or not track.get("mp3_path"):
            abort(404)

        mp3_rel = track["mp3_path"]
        # The seed (db/seed.py) stores paths relative to the canonical
        # album location at ~/OneDrive/Hermes/albums/<album>/. The
        # audio handler tries local candidates first (so dev iterations
        # without OneDrive still work), then falls back to the canonical
        # location (R10). All candidates are resolved as absolute
        # paths so the conditional=True send_file can do byte-range
        # requests on the actual file.
        album_id = track.get("album_id") or ""
        canonical = Path.home() / "OneDrive" / "Hermes" / "albums" / album_id
        candidates = [
            PROJ_ROOT / mp3_rel,
            PROJ_ROOT / "music" / Path(mp3_rel).name,
            canonical / mp3_rel,
            canonical / "music" / Path(mp3_rel).name,
        ]
        target = None
        for c in candidates:
            if c.exists() and c.is_file():
                target = c
                break
        if target is None:
            abort(404)

        return await send_file(str(target), conditional=True, mimetype="audio/mpeg")

    # === Day 4: albums + sessions handlers (split into modules) ===
    # The Blueprints from build/handlers_albums.py and
    # build/handlers_sessions.py own these route groups. We register
    # them here so the existing Day 3 architecture (one create_app()
    # factory, single route table) is preserved.
    app.register_blueprint(albums_bp)
    app.register_blueprint(sessions_bp)

    # === Day 5: events + decisions handlers (split into modules) ===
    # Same pattern as Day 4: each handler module owns its blueprint
    # and is registered here. These wrap db/events.py and
    # db/decisions.py respectively, which already shipped with the
    # db layer (tests in test_events.py + test_decisions.py cover
    # those at the db level).
    app.register_blueprint(events_bp)
    app.register_blueprint(decisions_bp)
    app.register_blueprint(build_bp)
    app.register_blueprint(intake_bp)


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
        # Day 8: sweeper thread lifecycle
        self._sweeper_threads: list = []
        self._sweeper_stop = None

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

    def start_sweepers(self) -> None:
        """Start Day 8 sweeper threads (idle_pause, wal_checkpoint, quota,
        mirror, log_rotate). Each runs in its own daemon thread so a
        broken sweeper can't crash the daemon. Stops on stop_sweepers().
        """
        try:
            from sweepers import start_all as sweepers_start
        except Exception as e:
            _log.warning(f"sweepers module unavailable, skipping: {e}")
            return
        self._sweeper_threads, self._sweeper_stop = sweepers_start()

    def stop_sweepers(self) -> None:
        """Signal all sweeper threads to exit and join them."""
        if not self._sweeper_threads or self._sweeper_stop is None:
            return
        try:
            from sweepers import stop_all as sweepers_stop
        except Exception as e:
            _log.warning(f"sweepers stop unavailable: {e}")
            return
        sweepers_stop(self._sweeper_threads, self._sweeper_stop, timeout=5.0)
        self._sweeper_threads = []
        self._sweeper_stop = None

    def run_migrations(self) -> None:
        # Local import so per-test tempdb isolation is honored.
        from db import run_migrations as _run_migrations
        result = _run_migrations()
        if result["errors"]:
            _log.error(f"migration errors: {result['errors']}")
            sys.exit(1)
        _log.info(f"migrations applied (schema_version={result['schema_version']})")

    def start(self) -> None:
        """Start the daemon (blocking until shutdown signal).

        Setup steps run inside a try block so any failure (lock error,
        migration error, etc.) releases the lock before sys.exit().
        Without this, a startup failure would leave the lock file on
        disk and block subsequent daemon starts until manually cleaned.
        """
        lock_acquired = False
        try:
            self.setup_logging()
            self.acquire_lock()
            lock_acquired = True
            self.run_migrations()
            self.install_signal_handlers()
            # Day 8: start sweepers BEFORE the HTTP server so health
            # checks can see them as "ok" from the very first request.
            self.start_sweepers()

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
            # Always release the lock, even if sys.exit(1) was called
            # by a setup step. The lock file on disk would otherwise
            # block the next daemon start (Finding #9).
            if lock_acquired:
                try:
                    self.lock.release()
                except Exception as e:
                    _log.warning(f"lock release failed during shutdown: {e}")
            # Day 8: stop sweeper threads before closing db conn
            try:
                self.stop_sweepers()
            except Exception as e:
                _log.warning(f"sweeper shutdown failed: {e}")
            try:
                from db.connection import close_db as _close_db
                _close_db()
            except Exception as e:
                _log.warning(f"db close failed during shutdown: {e}")


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
