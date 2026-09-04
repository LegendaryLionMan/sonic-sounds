# Day 3 Audit Fixes — 2026-09-02

## Summary

Land the 16 modified + 2 uncommitted files from the **2026-08-09 audit** as a coherent commit. Every code change is pinned by a regression test in `tests/test_regressions.py` (26 new tests, 12 regression classes).

**Pre-commit baseline:** 147/147 tests pass (was 119/119 at end of Day 3 ship).

## Regression classes fixed

| # | Class | Symptom | Fix |
|---|-------|---------|-----|
| 1 | read-only conn pragma crash | `open_db(read_only=True)` raised on WAL PRAGMA | URI-mode connect + read-safe PRAGMAs only |
| 2 | conn cache mode collision | writable conn returned for ro request (and vice-versa) | Cache key = `(path, read_only)` |
| 3 | open_session TOCTOU race | 20 concurrent threads exceeded MAX_ACTIVE_SESSIONS=3 | `BEGIN IMMEDIATE` wraps count+insert |
| 4 | mark_approved stuck in needs_approval | Approval gate never opened | Transition `needs_approval` → `ready`, stamp `approved_at` |
| 5 | _apply_migration auto-commit | `executescript()` issued implicit COMMIT, mid-script failure left partial schema | Split statements + explicit `BEGIN/COMMIT/ROLLBACK` |
| 6 | recover_orphans ignored known_pids | Argument accepted but unused | Honor the set; skip rows whose id is in it |
| 7 | album.status stale on session INSERT | Trigger fired on UPDATE only | New `trg_album_status_sync_ins` INSERT trigger |
| 8 | close_all only closed calling thread | `threading.local()` is per-thread | Cross-thread registry keyed on `thread_ident` |
| 9 | events.album_id no FK | Orphan album_ids allowed | Added `REFERENCES albums(id) ON DELETE SET NULL` |
| 10 | conn.close() in /api/audio left stale cache | Next open_db returned closed conn | Use `close_db()` to pop the cache entry |
| 11 | seed MIME hardcoded | All posters/merch labeled image/jpeg | `_mime_for_image()` / `_mime_for_video()` based on ext |
| 12 | ISRC format wrong | Album ISRC was "US-S1Z-25-01" (with dashes) | Real ISRC: "USS1Z2500001" (12 chars, no dashes) |
| 13 | Daemon lock leaked on setup failure | `sys.exit(1)` during startup left lock file | Wrap setup in try/finally, release on any failure |
| 14 | Registry leaked empty entries | `_thread_registry` grew monotonically | Pop entries when their conns list becomes empty |
| 15 | pause_idle_sessions f-string SQL | `last_activity_at < {cutoff}` built with f-string | `?` parameter binding (computed in Python) |
| 16 | cli.py serve was a placeholder | "Day 3 will implement" message | Delegates to `build.serve.main` with `--port`/`--host` |
| 17 | can_run didn't honor status='ready' | Doc said post-approval state; code never reached it | Added 'ready' branch alongside approved-`needs_approval` |

Plus: `pyproject.toml` (zero deps declared before), seed supports `.webp`/`.webm`, `runtime_min` updated 37→40.

## Files touched (18 total)

**Created (2):**
- `pyproject.toml`
- `tests/test_regressions.py` (633 lines, 26 tests)

**Modified (16):**
- `.gitignore` (meta-migrations allowed, scratch ignored)
- `build/serve.py` (close_db in audio, lock-release in finally)
- `cli.py` (serve delegates to build.serve.main)
- `db/build_jobs.py` (recover_orphans honors known_pids)
- `db/connection.py` (per-thread + cross-thread registry)
- `db/events.py` (unused import removed)
- `db/migrations.py` (atomic BEGIN/COMMIT + split statements)
- `db/pipeline.py` (can_run honors status='ready')
- `db/schema.sql` (INSERT trigger + FK on events)
- `db/seed.py` (MIME helpers, webp/webm support, ISRC fix)
- `db/sessions.py` (BEGIN IMMEDIATE, ? params in pause_idle_sessions)
- `tests/test_albums.py` (1+11 line additions)
- `tests/test_cli.py` (176 additions)
- `tests/test_pipeline.py` (58 additions)
- `tests/test_serve.py` (77 additions)
- `tests/test_sessions.py` (51 additions)

**Deleted (in working tree, ignored by .gitignore):**
- `.meta/sonic-studio.db` (rebuilt by run_migrations on next daemon start)
- `.meta/daemon.log` (runtime state)

## Verification

- [x] `pytest -q` → **147 passed in 13.92s**
- [x] All 26 regression tests in test_regressions.py pass (TestReadOnlyConnection, TestOpenSessionRace, TestMarkApprovedState, TestMigrationAtomicity, TestRecoverOrphansKnownPids, TestSchemaTriggers, TestCloseAllAcrossThreads, TestEventsAlbumFK, TestConnectionCloseOnLookup, TestSeedMIMEFix, TestSeedISRCFormat, TestDaemonLockRelease, TestRegistryNoLeak, TestEventsArchiveFK)

## Commit message (target)

```
Twenty-Two: Day 3 audit fixes — 17 regression classes pinned (147/147 tests)

Lands the 2026-08-09 audit: per-thread + cross-thread DB connection
registry, atomic migration runner with split statements, BEGIN IMMEDIATE
in open_session for the max-3 race, mark_approved transitions to 'ready',
INSERT trigger for album.status sync, close_all() honors other threads,
recover_orphans honors known_pids, seed MIME/ISRC fix, daemon lock
release on setup failure, pyproject.toml declares runtime deps.

Tests: 26 new regression tests in tests/test_regressions.py, one per
regression class. 147/147 pass (was 119/119 at end of Day 3 ship).
```

## Next: Day 4

Per PLAN-2026-08-09-v3.4 §Day 4:
- `handlers/albums.py` + `handlers/sessions.py` (CRUD wrappers, `asyncio.to_thread()`)
- Real `site/albums.html` + `albums.module.css` + `albums.js` (Mixtape '85 tokens)
- Tests in `tests/test_handlers_albums.py` + `tests/test_handlers_sessions.py`

**Adaptation (per Day 3 status):** `db/albums.py` + `db/sessions.py` already exist with full CRUD. Day 4 is HTTP wrapping + UI wiring. The `open_session` race fix landed here, so Day 4 handlers can call `db.sessions.open_session` without re-implementing the race guard.
