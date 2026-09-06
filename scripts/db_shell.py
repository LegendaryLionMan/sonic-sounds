"""scripts/db-shell - quick SQLite queries against the live daemon's DB.

Usage:
    python scripts/db-shell              # interactive REPL
    python scripts/db-shell "SELECT *"   # one-shot query
    python scripts/db-shell --tables      # list all tables
    python scripts/db-shell --dump       # dump schema as CREATE TABLE statements

This is a thin wrapper around sqlite3 that resolves the canonical
DB path (via SONIC_SOUNDS_DB_PATH env var or the default .meta
location) and prints results in a readable formatted table.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def resolve_db_path() -> Path:
    """Mirror db.connection.default_db_path() logic."""
    override = os.environ.get("SONIC_SOUNDS_DB_PATH")
    if override:
        return Path(override).resolve()
    return (ROOT / ".meta" / "sonic-sounds.db").resolve()


def format_table(cursor: sqlite3.Cursor, max_width: int = 40) -> str:
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()

    def truncate(s: str) -> str:
        s = str(s) if s is not None else "NULL"
        if len(s) > max_width:
            return s[:max_width - 1] + "\u2026"
        return s

    # Compute column widths
    widths = [len(c) for c in cols]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(truncate(val)))

    out = []
    sep = "+".join("-" * (w + 2) for w in widths)
    sep = f"+{sep}+"
    out.append(sep)
    out.append("| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(cols)) + " |")
    out.append(sep)
    for row in rows:
        out.append("| " + " | ".join(truncate(v).ljust(widths[i])
                                     for i, v in enumerate(row)) + " |")
    out.append(sep)
    out.append(f"{len(rows)} row(s)")
    return "\n".join(out)


def show_tables(conn: sqlite3.Connection) -> str:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    if not rows:
        return "(no tables)"
    return "\n".join(f"  {r[0]}" for r in rows)


def dump_schema(conn: sqlite3.Connection) -> str:
    rows = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL ORDER BY name"
    ).fetchall()
    if not rows:
        return "(no schema)"
    return "\n\n".join(r[0] + ";" for r in rows)


def interactive_loop(conn: sqlite3.Connection) -> None:
    print("sonic-sounds db shell")
    print(f"db: {Path(conn.execute('PRAGMA database_list').fetchone()[1]).name}")
    print("type '.tables' to list, '.schema' for ddl, '.quit' to exit, "
          "or any SQL.")
    while True:
        try:
            buf = input("db> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not buf:
            continue
        if buf in (".quit", ".exit"):
            break
        if buf == ".tables":
            print(show_tables(conn))
            continue
        if buf == ".schema":
            print(dump_schema(conn))
            continue
        try:
            cur = conn.execute(buf)
            if cur.description:
                print(format_table(cur))
            else:
                # DML/DDL — no result set
                conn.commit()
                print("OK")
        except sqlite3.Error as e:
            print(f"sqlite error: {e}")


def main() -> int:
    p = argparse.ArgumentParser(description="sonic-sounds db shell")
    p.add_argument("query", nargs="?", help="one-shot SQL query (else interactive)")
    p.add_argument("--tables", action="store_true", help="list all tables")
    p.add_argument("--dump", action="store_true", help="dump schema as CREATE TABLE")
    p.add_argument("--db", type=Path, default=None,
                   help="explicit db path (default: SONIC_SOUNDS_DB_PATH or .meta/sonic-sounds.db)")
    args = p.parse_args()

    db = args.db or resolve_db_path()
    if not db.exists():
        print(f"db not found: {db}")
        print("  hint: start the daemon first or use --db <path>")
        return 1

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        if args.tables:
            print(show_tables(conn))
            return 0
        if args.dump:
            print(dump_schema(conn))
            return 0
        if args.query:
            cur = conn.execute(args.query)
            if cur.description:
                print(format_table(cur))
            return 0
        interactive_loop(conn)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
