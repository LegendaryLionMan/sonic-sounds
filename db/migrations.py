"""db/migrations.py — version-based, idempotent migration runner (per Q24, Q26 v3.2 §Day 2).

Per the plan:
- db/migrations.py: version-based, idempotent
- Migrations live in .meta/migrations/ as numbered files (e.g. 001_initial.sql)
- Each migration has a "version" row in db_meta; runner applies only when version > current
- The schema.sql is the initial migration (001_initial.sql)

This module is the runner. The migration files are stored in
.meta/migrations/ alongside the database. The runner is called on:
- Daemon startup (per Day 3)
- Health check endpoint (per Day 3)
- Manual CLI invocation: `python -m db.migrations`

Design:
- A `db_meta` table stores the current schema version
- Migrations are <version>_<description>.sql files in order
- Each migration is wrapped in a transaction; if it fails, the version is NOT bumped
- Idempotent: re-running on a fully-up-to-date DB is a no-op
"""
import sqlite3
from pathlib import Path
from typing import Union

from db.connection import open_db, DEFAULT_DB_PATH

# Migrations directory: .meta/migrations/
MIGRATIONS_DIR = DEFAULT_DB_PATH.parent / "migrations"

# Tricky: when running tests, we want migrations to live next to the test
# db's .meta. The runner resolves this dynamically.
def _resolve_migrations_dir(db_path: Union[str, Path]) -> Path:
    """Resolve the migrations directory from the db's expected location."""
    return Path(db_path).parent / "migrations"


def _ensure_db_meta(conn: sqlite3.Connection) -> None:
    """Create the db_meta table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS db_meta (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()


def _get_current_schema_version(conn: sqlite3.Connection) -> int:
    """Return the current schema version. 0 if no migrations applied yet."""
    _ensure_db_meta(conn)
    row = conn.execute(
        "SELECT value FROM db_meta WHERE key = 'schema_version'"
    ).fetchone()
    if not row:
        return 0
    try:
        return int(row["value"])
    except (ValueError, TypeError):
        return 0


def _set_current_schema_version(conn: sqlite3.Connection,
                               version: int) -> None:
    """Set the schema version (after a migration succeeds)."""
    conn.execute("""
        INSERT INTO db_meta (key, value) VALUES ('schema_version', ?)
        ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = datetime('now')
    """, (str(version), str(version)))
    conn.commit()


def _discover_migrations(migrations_dir: Path) -> list[tuple[int, str, Path]]:
    """Discover all migration files in MIGRATIONS_DIR.

    Returns a sorted list of (version, description, path) tuples.
    Migrations files are named <version>_<description>.sql.
    Version is parsed as the leading integer.
    """
    if not migrations_dir.exists():
        return []
    out = []
    for f in sorted(migrations_dir.glob("*.sql")):
        # Parse "NNN_description.sql"
        parts = f.stem.split("_", 1)
        if len(parts) < 2:
            continue
        try:
            version = int(parts[0])
        except ValueError:
            continue
        description = parts[1]
        out.append((version, description, f))
    return sorted(out)


def _apply_migration(conn: sqlite3.Connection,
                     version: int,
                     description: str,
                     path: Path) -> None:
    """Apply a single migration in a transaction."""
    sql = path.read_text(encoding="utf-8")
    # SQL files can have multiple statements separated by semicolons
    # exec_script handles that correctly
    try:
        conn.executescript(sql)
        # Apply the schema migrations — db_meta is updated LAST so that
        # partial migrations don't bump the version.
        conn.execute("""
            INSERT INTO db_meta (key, value) VALUES ('schema_version', ?)
            ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = datetime('now')
        """, (str(version), str(version)))
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise


def run_migrations(db_path: Union[str, Path, None] = None) -> dict:
    """Apply all pending migrations to the database.

    Args:
        db_path: target db. Defaults to None (use open_db default).

    Returns a summary dict:
      {
        "schema_version": int,    # current version after migration
        "applied": list[(int, str)],  # (version, description) tuples that were applied
        "skipped": list[(int, str)],  # tuples already applied
        "errors": list[str],         # any migration errors
      }
    """
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    conn = open_db(path)
    migrations_dir = _resolve_migrations_dir(path)
    # If no migrations dir exists, try the canonical .meta/migrations/ as a fallback
    if not migrations_dir.exists():
        canonical = DEFAULT_DB_PATH.parent / "migrations"
        if canonical.exists() and canonical != migrations_dir:
            migrations_dir = canonical

    current = _get_current_schema_version(conn)
    discovered = _discover_migrations(migrations_dir)

    applied = []
    skipped = []
    errors = []

    for version, description, file_path in discovered:
        if version <= current:
            skipped.append((version, description))
            continue
        try:
            _apply_migration(conn, version, description, file_path)
            applied.append((version, description))
        except sqlite3.Error as e:
            errors.append(f"Migration {version:03d} ({description}) failed: {e}")
            break

    return {
        "schema_version": _get_current_schema_version(conn),
        "applied": applied,
        "skipped": skipped,
        "errors": errors,
        "db_path": str(path),
    }


def bootstrap_initial_migration(db_path: Union[str, Path, None] = None) -> bool:
    """If no migrations exist yet, write the initial schema migration.

    The initial schema is in db/schema.sql. We copy it into .meta/migrations/
    as 001_initial_schema.sql and run it. Returns True if bootstrapped.
    """
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    migrations_dir = _resolve_migrations_dir(path)
    migrations_dir.mkdir(parents=True, exist_ok=True)

    initial_path = migrations_dir / "001_initial_schema.sql"
    if initial_path.exists():
        return False

    schema_src = Path("db/schema.sql")
    if not schema_src.exists():
        return False

    initial_path.write_text(schema_src.read_text(encoding="utf-8"), encoding="utf-8")
    return True


# === Module-level CLI ===

def main():
    """CLI: python -m db.migrations"""

    import argparse
    import sys
    parser = argparse.ArgumentParser(description="Run album-studio db migrations")
    parser.add_argument("--db", type=Path, default=None,
                        help=f"Path to db (default: {DEFAULT_DB_PATH})")
    parser.add_argument("--bootstrap", action="store_true",
                        help="Bootstrap the initial migration from db/schema.sql")
    parser.add_argument("--status", action="store_true",
                        help="Show current schema version")
    args = parser.parse_args()

    if args.bootstrap:
        # Copy db/schema.sql → .meta/migrations/001_initial_schema.sql
        bootstrapped = bootstrap_initial_migration(args.db)
        if bootstrapped:
            print(f"Bootstrapped initial migration from db/schema.sql")
        else:
            print(f"Initial migration already exists")

    if args.status:
        conn = open_db(args.db)
        v = _get_current_schema_version(conn)
        print(f"Current schema version: {v}")

    result = run_migrations(args.db)
    print(f"DB: {result['db_path']}")
    print(f"Schema version after: {result['schema_version']}")
    if result["applied"]:
        print(f"Applied: {result['applied']}")
    if result["skipped"]:
        print(f"Skipped (already applied): {len(result['skipped'])} migration(s)")
    if result["errors"]:
        print(f"ERRORS: {result['errors']}")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
