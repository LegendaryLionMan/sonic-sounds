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

# Canonical migrations directory (always points at the project repo,
# NOT at DEFAULT_DB_PATH.parent). When SONIC_SOUNDS_DB_PATH redirects
# the database to a tempdir (e.g. in tests), migrations should still
# come from the project's canonical location, not from a phantom
# "tempdir/migrations/" dir.
_PROJ_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_META_DIR = _PROJ_ROOT / ".meta"
MIGRATIONS_DIR = _PROJECT_META_DIR / "migrations"

# Migrations always live in the project's canonical .meta/migrations/.
# They do NOT live next to the database file, so this works correctly
# even when SONIC_SOUNDS_DB_PATH points the database at a tempdir.
def _resolve_migrations_dir(db_path: Union[str, Path]) -> Path:
    """Return the canonical migrations dir (always project-relative)."""
    return MIGRATIONS_DIR


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
    """Apply a single migration in a transaction.

    executescript() issues an implicit COMMIT before running its SQL, which
    terminates any active transaction. Wrapping it in BEGIN/ROLLBACK therefore
    provides no atomicity guarantee. Instead, we split the migration SQL on
    semicolons and run each statement via conn.execute() inside an explicit
    BEGIN/COMMIT, so a mid-script failure truly rolls back.

    The schema_version row is bumped in the same transaction, so a failed
    migration leaves both schema and version unchanged.
    """
    sql = path.read_text(encoding="utf-8")
    # Split into individual statements. exec_script handles comments
    # poorly when split naively, so we strip line comments first.
    statements = [s.strip() for s in _split_sql_statements(sql) if s.strip()]

    try:
        conn.execute("BEGIN;")
        try:
            for stmt in statements:
                conn.execute(stmt)
            # Bump the version LAST and in the same transaction so the
            # version reflects only fully-applied migrations.
            conn.execute("""
                INSERT INTO db_meta (key, value) VALUES ('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = datetime('now')
            """, (str(version), str(version)))
            conn.execute("COMMIT;")
        except sqlite3.Error:
            try:
                conn.execute("ROLLBACK;")
            except sqlite3.Error:
                pass
            raise
    except sqlite3.Error:
        raise


def _split_sql_statements(sql: str) -> list[str]:
    """Split a SQL script into individual statements.

    Tracks BEGIN...END nesting (used in triggers and CASE expressions) so
    that semicolons inside those blocks don't prematurely terminate the
    outer statement. Also strips line comments (-- ...).

    Sufficient for our schema.sql and migration files.
    """
    # Remove line comments.
    cleaned_lines = []
    for line in sql.splitlines():
        idx = line.find("--")
        if idx >= 0:
            line = line[:idx]
        cleaned_lines.append(line)
    cleaned = "\n".join(cleaned_lines)

    # Tokenize-aware split: walk char by char, track depth of BEGIN...END,
    # split on ';' only at depth 0 and outside string literals.
    statements = []
    buf: list[str] = []
    depth = 0
    in_string = False
    string_char = None
    i = 0
    while i < len(cleaned):
        ch = cleaned[i]
        # String literal handling: single or double quote
        if in_string:
            buf.append(ch)
            if ch == string_char:
                # Check for escape: '' inside single-quoted string
                if i + 1 < len(cleaned) and cleaned[i + 1] == string_char:
                    buf.append(cleaned[i + 1])
                    i += 2
                    continue
                in_string = False
            i += 1
            continue
        if ch in ("'", '"'):
            in_string = True
            string_char = ch
            buf.append(ch)
            i += 1
            continue
        # Track BEGIN...END depth (case-insensitive)
        if cleaned[i:i+5].upper() == "BEGIN" and (i + 5 >= len(cleaned) or not cleaned[i+5].isalpha()):
            depth += 1
            buf.append(ch)
            i += 1
            continue
        if cleaned[i:i+3].upper() == "END" and (i + 3 >= len(cleaned) or not cleaned[i+3].isalpha()):
            # Only treat END as a block closer if it's followed by ; or whitespace+; or EOL.
            # CASE...END expressions end with `END,` (followed by comma); trigger bodies
            # end with `END;`. The discriminator is the character after END.
            next_ch = cleaned[i+3] if i + 3 < len(cleaned) else ""
            if next_ch == ";" or next_ch == "" or next_ch in " \t\n":
                if depth > 0:
                    depth -= 1
            buf.append(ch)
            i += 1
            continue
        if ch == ";" and depth == 0:
            stmt = "".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1

    # Trailing statement without semicolon
    stmt = "".join(buf).strip()
    if stmt:
        statements.append(stmt)
    return statements


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

    # Resolve schema.sql relative to the db package, not CWD. Service-mode
    # daemons have a CWD of C:\Windows\System32 and would fail to find
    # "db/schema.sql" via a CWD-relative path.
    schema_src = Path(__file__).resolve().parent / "schema.sql"
    if not schema_src.exists():
        return False

    initial_path.write_text(schema_src.read_text(encoding="utf-8"), encoding="utf-8")
    return True


# === Module-level CLI ===

def main():
    """CLI: python -m db.migrations"""

    import argparse
    import sys
    parser = argparse.ArgumentParser(description="Run sonic-sounds db migrations")
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
