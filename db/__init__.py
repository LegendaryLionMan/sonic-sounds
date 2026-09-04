"""db/__init__.py — package entry point for sonic-studio db.

Per plan §7 Day 2 verification:
"python -c \"from tools.sonic_studio.db import open_db; open_db()\" → opens, runs migrations, PRAGMAs verified"

Note: the plan's path `tools.sonic_studio.db` was structural at v3.2 time.
v3.4 patches it to `db` (the actual project layout per STRUCTURE-POLICY.md).
The first import below maintains backward compatibility for daemon code that
expects `tools.sonic_studio.db` as the import path.

Public API:
- open_db(db_path=None) — opens a SQLite connection with WAL + PRAGMAs
- close_db(db_path=None) — closes a cached connection
- close_all() — closes all cached connections
- run_migrations(db_path=None) — applies pending migrations
"""
# Connection management
from db.connection import (
    open_db,
    close_db,
    close_all,
    db_path,
    DEFAULT_DB_PATH,
)

# Migration runner
from db.migrations import (
    run_migrations,
    bootstrap_initial_migration,
)

# Pipeline read-side (Phase 0.D)
from db.pipeline import (
    can_run,
    next_runnable,
    mark_approved,
    layer_status,
    all_layers,
    LAYER_ORDER,
    APPROVAL_REQUIRED,
)

# Schema constants
__version__ = "0.0.1"
__all__ = [
    "open_db",
    "close_db",
    "close_all",
    "db_path",
    "DEFAULT_DB_PATH",
    "run_migrations",
    "bootstrap_initial_migration",
    "can_run",
    "next_runnable",
    "mark_approved",
    "layer_status",
    "all_layers",
    "LAYER_ORDER",
    "APPROVAL_REQUIRED",
]
