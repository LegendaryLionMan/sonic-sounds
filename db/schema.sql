-- db/schema.sql
-- Phase 0.A + Day 2: minimum 4 tables for seed (artists, albums, tracks, assets)
-- + 9 more for Day 2 (sessions, events, decisions, build_jobs, quota_snapshots,
--   album_briefs, lyrics, generation_manifests, audit_log)
-- Per PLAN-2026-07-28-v3.2 §Day 2 + Phase 0.A
--
-- All timestamps stored as ISO-8601 text. WAL mode enabled in db/connection.py.
-- Foreign keys enforced.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- === Phase 0.A: minimum 4 tables for Maren Sol seed ===

CREATE TABLE IF NOT EXISTS artists (
    id              TEXT PRIMARY KEY,           -- slug (e.g. "maren-sol")
    name            TEXT NOT NULL UNIQUE,
    persona         TEXT,
    hometown_city   TEXT,
    hometown_region TEXT,
    hometown_country TEXT,
    formed_year     INTEGER,
    is_fictional    INTEGER NOT NULL DEFAULT 0, -- 0/1
    is_default      INTEGER NOT NULL DEFAULT 0, -- 0/1
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS albums (
    id              TEXT PRIMARY KEY,           -- slug (e.g. "half-light-hours")
    title           TEXT NOT NULL,
    primary_artist_id TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active',  -- active | done | archived
    release_date    TEXT,
    runtime_min     INTEGER,                    -- total runtime minutes
    cover_path      TEXT,
    cassette_sticker_path TEXT,
    isrc            TEXT,                       -- primary ISRC
    m09_sonic_dna   TEXT,                       -- JSON blob (per v2.2 schema)
    locked_at       TEXT,                       -- when M-locks were finalized
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (primary_artist_id) REFERENCES artists(id)
);

CREATE TABLE IF NOT EXISTS tracks (
    id              TEXT PRIMARY KEY,           -- "<album-slug>:<track-num>"
    album_id        TEXT NOT NULL,
    track_num       INTEGER NOT NULL,
    title           TEXT NOT NULL,
    duration_sec    INTEGER,
    isrc            TEXT,                       -- track-level ISRC
    lyrics_path     TEXT,
    lrc_path        TEXT,
    mp3_path        TEXT,
    cover_path      TEXT,
    mood            TEXT,                       -- hand-written mood descriptor
    status          TEXT NOT NULL DEFAULT 'todo',  -- todo | drafted | recorded | mastered | tagged
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (album_id, track_num),
    FOREIGN KEY (album_id) REFERENCES albums(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS assets (
    id              TEXT PRIMARY KEY,           -- "<album-slug>:<asset-name>"
    album_id        TEXT NOT NULL,
    kind            TEXT NOT NULL,              -- cover | poster | cassette | lyric | audio | video | social
    path            TEXT NOT NULL,              -- absolute or canonical-relative path
    mime            TEXT,                       -- mime type
    width           INTEGER,                    -- image/video width
    height          INTEGER,                    -- image/video height
    size_bytes      INTEGER,
    sha256          TEXT,                       -- content hash
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (album_id) REFERENCES albums(id) ON DELETE CASCADE
);

-- === Day 2: 9 more tables for the daemon ===

-- Sessions (per Q27 — album_sessions is first-class)
CREATE TABLE IF NOT EXISTS album_sessions (
    id              TEXT PRIMARY KEY,           -- uuid
    album_id        TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active',  -- active | paused | done | blocked
    last_activity_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    closed_at       TEXT,
    FOREIGN KEY (album_id) REFERENCES albums(id) ON DELETE CASCADE
);
-- Q32: max 3 active sessions enforced in CLI, not schema
CREATE INDEX IF NOT EXISTS idx_sessions_status ON album_sessions(status, last_activity_at);
-- Q32: 12h idle auto-pause sweep reads this index

-- Events (chat, build, system) — Q34
CREATE TABLE IF NOT EXISTS events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    album_id        TEXT,                       -- nullable (some events are global)
    role            TEXT NOT NULL,              -- user | assistant | system | tool
    kind            TEXT NOT NULL,              -- chat | build | quota | system | log
    content         TEXT,                       -- main text content
    payload_json    TEXT,                       -- structured data (build_args, mmx response, etc)
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES album_sessions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_events_session_time ON events(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_events_album_time ON events(album_id, created_at);

-- Decisions (Aldecision Verdicts from META-DECISIONS)
CREATE TABLE IF NOT EXISTS decisions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT,
    album_id        TEXT,
    code            TEXT NOT NULL,              -- e.g. "Q21", "M08", "M09"
    tier            TEXT NOT NULL,              -- mandatory | recommended | extra
    question        TEXT,                       -- the verbatim question
    answer          TEXT,                       -- the verbatim answer
    rationale       TEXT,                       -- why this answer
    locked_at       TEXT,                       -- when the answer was locked
    source_doc      TEXT,                       -- which META-DECISIONS file
    FOREIGN KEY (session_id) REFERENCES album_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (album_id) REFERENCES albums(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_decisions_album_code ON decisions(album_id, code);

-- Build jobs (per Phase 0.D + Day 6) — 12-layer pipeline
CREATE TABLE IF NOT EXISTS build_jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    album_id        TEXT NOT NULL,
    layer_id        TEXT NOT NULL,              -- 01..12 from LAYER_ORDER
    status          TEXT NOT NULL DEFAULT 'todo',  -- todo | needs_approval | ready | running | done | blocked
    approved_at     TEXT,
    started_at      TEXT,
    completed_at    TEXT,
    error           TEXT,
    attempts        INTEGER NOT NULL DEFAULT 0,
    last_event_id   INTEGER,                    -- link to events
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (album_id, layer_id),
    FOREIGN KEY (album_id) REFERENCES albums(id) ON DELETE CASCADE,
    FOREIGN KEY (last_event_id) REFERENCES events(id)
);
CREATE INDEX IF NOT EXISTS idx_build_jobs_album_status ON build_jobs(album_id, status);

-- Quota snapshots (per Day 8 quota sweeper)
CREATE TABLE IF NOT EXISTS quota_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    model_kind      TEXT NOT NULL,              -- general | video | speech
    interval_pct    REAL NOT NULL,             -- 0.0 - 100.0
    interval_remaining_ms INTEGER,
    captured_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_quota_captured ON quota_snapshots(captured_at);

-- Album briefs (the locked concept-brief per album)
CREATE TABLE IF NOT EXISTS album_briefs (
    album_id        TEXT PRIMARY KEY,
    brief_json      TEXT NOT NULL,              -- serialized concept-brief
    locked_decisions_json TEXT,                 -- the locked Q-decisions
    sonic_dna_json   TEXT,                       -- M09 snapshot
    generated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (album_id) REFERENCES albums(id) ON DELETE CASCADE
);

-- Lyrics (per-track synced + unsynced)
CREATE TABLE IF NOT EXISTS lyrics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id        TEXT NOT NULL,
    format          TEXT NOT NULL,              -- md | lrc
    content         TEXT NOT NULL,
    checksum        TEXT,                       -- sha256
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (track_id, format),
    FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE
);

-- Generation manifests (per v2.2 — every mmx music generate has a sibling)
CREATE TABLE IF NOT EXISTS generation_manifests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id        TEXT NOT NULL,
    manifest_json   TEXT NOT NULL,              -- the .generation-manifest.json content
    mmx_action      TEXT NOT NULL,              -- "music generate" | "image generate" | etc
    mmx_args_json   TEXT NOT NULL,              -- exact args sent
    result_path     TEXT,                       -- path to the artifact produced
    result_sha256   TEXT,                       -- fingerprint of the output
    captured_at     TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (track_id, captured_at),
    FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE
);

-- Audit log (catch-all for daemon events that don't fit elsewhere)
CREATE TABLE IF NOT EXISTS audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    actor           TEXT,                       -- "user" | "penelope" | "daemon" | "cli" | null
    action          TEXT NOT NULL,              -- "build.start" | "build.complete" | etc
    target          TEXT,                       -- "<table>:<id>" reference
    payload_json    TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);

-- === Triggers ===

-- Q27: album.status is derived from album_sessions.status (no manual mutation)
CREATE TRIGGER IF NOT EXISTS trg_album_status_sync
AFTER UPDATE OF status ON album_sessions
FOR EACH ROW
WHEN NEW.album_id IS NOT NULL
BEGIN
    UPDATE albums
    SET status = CASE
        WHEN (SELECT COUNT(*) FROM album_sessions
              WHERE album_id = NEW.album_id AND status = 'done') > 0
            THEN 'done'
        WHEN (SELECT COUNT(*) FROM album_sessions
              WHERE album_id = NEW.album_id AND status = 'active') > 0
            THEN 'active'
        WHEN (SELECT COUNT(*) FROM album_sessions
              WHERE album_id = NEW.album_id AND status = 'paused') > 0
            THEN 'paused'
        ELSE 'archived'
    END,
    updated_at = datetime('now')
    WHERE id = NEW.album_id;
END;
