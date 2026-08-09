# db/ — album-studio database layer

Per PLAN-2026-07-28-v3.4 §Day 2.

Public API (importable from `db`):
- `open_db(db_path=None, *, read_only=False)` — open a SQLite connection with WAL + PRAGMAs
- `close_db(db_path=None)` / `close_all()` — close cached connection(s)
- `run_migrations(db_path=None)` — apply pending migrations; returns `{schema_version, applied, skipped, errors}`
- `bootstrap_initial_migration(db_path=None)` — copy `db/schema.sql` → `.meta/migrations/001_initial_schema.sql`

Read-side (per Phase 0.D, `db/pipeline.py`):
- `LAYER_ORDER` — 12 layers in pipeline order
- `APPROVAL_REQUIRED` — 6 layers that need user approval
- `can_run(layer_id, album_id)` / `next_runnable(album_id)` / `mark_approved(layer_id, album_id)`
- `layer_status(layer_id, album_id)` / `all_layers(album_id)`

CRUD (per Day 2.4):
- `db.albums`: artists, albums, tracks, assets (list/get/create/update/delete + archive_album)
- `db.sessions`: open, pause, resume, complete + max-3 guard + 12h idle
- `db.events`: paginated event log (Q34) with `?since=<ts>` pagination
- `db.decisions`: Aldecision Verdicts (Q30) — M/R/E tier + locked_at + source_doc
- `db.build_jobs`: queue, mark_running, mark_succeeded, mark_failed, recover_orphans
- `db.queries`: dashboard_summary, recent_albums_with_progress, session_chat_history, build_jobs_for_album, global_status, format_status_4line

## Default DB location
`.meta/album-studio.db` (per Q25)

## 13 tables (per Q23, expanded by Q27)
- artists, albums, tracks, assets (4 core)
- album_sessions (Q27)
- events (Q34)
- decisions (Q30)
- build_jobs (Q29)
- quota_snapshots (Day 8)
- album_briefs, lyrics, generation_manifests (Day 9)
- audit_log (Day 9)

Plus 1 trigger: `trg_album_status_sync` (Q27) — album.status derived from session states.

## PRAGMAs (per Q26)
- `PRAGMA journal_mode = WAL` (write-ahead log)
- `PRAGMA foreign_keys = ON` (FK enforcement)
- `PRAGMA synchronous = NORMAL` (WAL-safe)
- `PRAGMA busy_timeout = 5000` (5s wait for lock)
- `PRAGMA cache_size = -8000` (8 MB cache)
- `PRAGMA temp_store = MEMORY` (temp tables in memory)
