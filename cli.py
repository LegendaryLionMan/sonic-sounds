"""cli.py + __main__.py — LOCKED verb surface (per v3.2 §Day 2 + §7).

Per the plan:
- cli.py + __main__.py with the LOCKED verb surface (serve, status,
  list albums, list sessions, chat, pause/resume/complete, invoke, finalize)
- Migrate any existing JSON state.json → SQLite (one-time script)

This module is the embeddability contract per v3.2 §7: every operation
the user does via the UI is also a CLI verb. The CLI is how the daemon
gets started, and how scripts can do everything the UI does.

Usage:
  python -m cli serve --port=8765 --db=.meta/sonic-sounds.db
  python -m cli status
  python -m cli list albums
  python -m cli list sessions --album=half-light-hours
  python -m cli chat --session=<uuid> --message="..."
  python -m cli pause <session-uuid>
  python -m cli resume <session-uuid>
  python -m cli complete <session-uuid>
  python -m cli invoke <action>  (Day 6 — placeholder for now)
  python -m cli finalize <album-slug>  (Day 11 — placeholder for now)
"""
import argparse
import sys
from pathlib import Path
from typing import Optional

from db import DEFAULT_DB_PATH
from db.albums import (
    list_artists, list_albums, get_album,
    list_tracks, get_artist,
)
from db.sessions import (
    list_sessions, get_session, open_session,
    pause_session, resume_session, complete_session,
    count_active_sessions, MAX_ACTIVE_SESSIONS,
)
from db.events import create_event
from db.queries import global_status, format_status_4line


def cmd_serve(args) -> int:
    """Start the daemon (Day 3 implementation).

    Delegates to build.serve.main so `python -m cli serve` starts the
    Quart daemon on the requested port (the placeholder message was
    Day 2's scaffolding and is no longer accurate now that Day 3 is
    implemented).
    """
    from build.serve import main as serve_main
    # Forward --port and --host to the daemon
    sys.argv = ["build.serve", f"--port={args.port}", f"--host={args.host}"]
    return serve_main()


def cmd_status(args) -> int:
    """Print the 4-line status (per plan §7 Day 2 verification)."""
    status = global_status(args.db)
    print(format_status_4line(status))
    return 0


def cmd_list(args) -> int:
    """List albums or sessions."""
    if args.what == "albums":
        rows = list_albums(db_path=args.db)
        if not rows:
            print("(no albums)")
            return 0
        print(f"{'ID':<30} {'TITLE':<40} {'STATUS':<10} {'CREATED'}")
        for r in rows:
            print(f"{r['id']:<30} {r['title']:<40} {r['status']:<10} {r['created_at']}")
    elif args.what == "sessions":
        rows = list_sessions(album_id=args.album, db_path=args.db)
        if not rows:
            print("(no sessions)")
            return 0
        print(f"{'ID':<40} {'ALBUM':<30} {'STATUS':<10} {'LAST ACTIVITY'}")
        for r in rows:
            print(f"{r['id']:<40} {r['album_id']:<30} {r['status']:<10} {r['last_activity_at']}")
    elif args.what == "artists":
        rows = list_artists(db_path=args.db)
        if not rows:
            print("(no artists)")
            return 0
        print(f"{'ID':<30} {'NAME':<40}")
        for r in rows:
            print(f"{r['id']:<30} {r['name']:<40}")
    return 0


def cmd_chat(args) -> int:
    """Append a user message to events."""
    if not args.session or not args.message:
        print("chat requires --session=<uuid> and --message=...", file=sys.stderr)
        return 1
    e = create_event(args.session, "user", "chat", args.message, db_path=args.db)
    print(f"event_id: {e['id']}")
    return 0


def cmd_pause(args) -> int:
    """Pause a session."""
    if not args.target:
        print("pause requires a session uuid", file=sys.stderr)
        return 1
    s = pause_session(args.target, db_path=args.db)
    if s is None:
        print(f"pause failed: session {args.target} not found or invalid state", file=sys.stderr)
        return 1
    print(f"paused: {s['id']} status={s['status']}")
    return 0


def cmd_resume(args) -> int:
    """Resume a session."""
    if not args.target:
        print("resume requires a session uuid", file=sys.stderr)
        return 1
    s = resume_session(args.target, db_path=args.db)
    if s is None:
        print(f"resume failed: session {args.target} not found, paused, or max-3 active exceeded", file=sys.stderr)
        return 1
    print(f"resumed: {s['id']} status={s['status']}")
    return 0


def cmd_complete(args) -> int:
    """Complete a session."""
    if not args.target:
        print("complete requires a session uuid", file=sys.stderr)
        return 1
    s = complete_session(args.target, db_path=args.db)
    if s is None:
        print(f"complete failed: session {args.target} not found or already done", file=sys.stderr)
        return 1
    print(f"completed: {s['id']} status={s['status']}")
    return 0


def cmd_invoke(args) -> int:
    """Invoke an action via the build runner. Day 6 will implement."""
    if not args.action:
        print("invoke requires <action>", file=sys.stderr)
        return 1
    print(f"invoke {args.action}: Day 6 will implement the build runner.")
    print("  - Day 2: placeholder, not yet wired")
    return 0


def cmd_finalize(args) -> int:
    """Finalize an album. Day 11 will implement."""
    if not args.target:
        print("finalize requires <album-slug>", file=sys.stderr)
        return 1
    print(f"finalize {args.target}: Day 11 will implement.")
    return 0


def cmd_migrate(args) -> int:
    """One-time migration: any existing JSON state.json → SQLite. Day 2."""
    src = args.from_json
    if not src:
        # Look for default state.json locations
        candidates = [
            Path(".meta/state.json"),
            Path(".meta/albums.json"),
            Path("albums.json"),
        ]
        for c in candidates:
            if c.exists():
                src = c
                break
    if not src or not Path(src).exists():
        print(f"migrate: no JSON state file found. Use --from-json=path/to/file.json")
        return 0
    print(f"migrate: reading {src} → {args.db}")
    print("  - Day 2: scaffold only. JSON state.json migration is a one-time script.")
    return 0


# === MAIN ===

def main():
    parser = argparse.ArgumentParser(
        description="sonic-sounds CLI — LOCKED verb surface per PLAN-2026-07-28-v3.4",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Locked verbs (per plan §7):
  serve                          start daemon (Day 3)
  status                         4-line status
  list <albums|sessions|artists>  table view
  chat --session=<uuid> --message="..."
  pause <session-uuid>            active|blocked -> paused
  resume <session-uuid>           paused|blocked -> active
  complete <session-uuid>         -> done
  invoke <action>                 one mmx call (Day 6)
  finalize <album-slug>           -> done (Day 11)
  migrate --from-json=path        one-time JSON state migration
""")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH,
                        help=f"Path to db (default: {DEFAULT_DB_PATH})")

    subparsers = parser.add_subparsers(dest="command", help="command (see epilog)")

    # serve
    p_serve = subparsers.add_parser("serve", help="start the daemon")
    p_serve.add_argument("--port", type=int, default=8765)
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.set_defaults(func=cmd_serve)

    # status
    p_status = subparsers.add_parser("status", help="4-line status summary")
    p_status.set_defaults(func=cmd_status)

    # list
    p_list = subparsers.add_parser("list", help="list albums/sessions/artists")
    p_list.add_argument("what", choices=["albums", "sessions", "artists"])
    p_list.add_argument("--album", help="filter sessions by album")
    p_list.set_defaults(func=cmd_list)

    # chat
    p_chat = subparsers.add_parser("chat", help="append user message to events")
    p_chat.add_argument("--session", help="session uuid")
    p_chat.add_argument("--message", help="message text")
    p_chat.set_defaults(func=cmd_chat)

    # pause
    p_pause = subparsers.add_parser("pause", help="pause a session")
    p_pause.add_argument("target", nargs="?", help="session uuid")
    p_pause.set_defaults(func=cmd_pause)

    # resume
    p_resume = subparsers.add_parser("resume", help="resume a session")
    p_resume.add_argument("target", nargs="?", help="session uuid")
    p_resume.set_defaults(func=cmd_resume)

    # complete
    p_complete = subparsers.add_parser("complete", help="complete a session")
    p_complete.add_argument("target", nargs="?", help="session uuid")
    p_complete.set_defaults(func=cmd_complete)

    # invoke
    p_invoke = subparsers.add_parser("invoke", help="invoke a build action (Day 6)")
    p_invoke.add_argument("action", nargs="?", help="action name")
    p_invoke.set_defaults(func=cmd_invoke)

    # finalize
    p_finalize = subparsers.add_parser("finalize", help="finalize an album (Day 11)")
    p_finalize.add_argument("target", nargs="?", help="album slug")
    p_finalize.set_defaults(func=cmd_finalize)

    # migrate
    p_migrate = subparsers.add_parser("migrate", help="migrate JSON state to SQLite")
    p_migrate.add_argument("--from-json", help="path to JSON state file")
    p_migrate.set_defaults(func=cmd_migrate)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
