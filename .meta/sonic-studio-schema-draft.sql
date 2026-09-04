-- sonic-studio SQLite Schema — DRAFT v0.2 (NOT YET APPLIED)
--
-- Source: planning/PLAN-2026-07-28-v3.2.md § 4 (folder structure)
--         and § 6 (pipeline-deps.json dependency graph)
-- Status:   DRAFT, 2026-07-30, REVIEW-READY
--
-- 13 tables, all FK relationships defined, partial UNIQUE index from Q29f,
-- triggers for derived columns from Q27, WAL mode set in connection.py.
--
-- Design rules:
-- - snake_case table + column names
-- - all timestamps: TEXT in ISO 8601 UTC
-- - all UUIDs: TEXT (32 hex chars) — no extension dependency
-- - enums: CHECK constraints with IN(...)
-- - inline CHECK on column for type safety, table-level CHECK not used
-- - indexes added for hot query paths
-- - triggers compute derived values (albums.status from album_sessions)

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;  -- set in connection.py, not here

-- ============================================================================
-- 1. artists — the persona
-- ============================================================================

CREATE TABLE artists (
    id              TEXT PRIMARY KEY,
    slug            TEXT NOT NULL UNIQUE,
    stage_name      TEXT NOT NULL,
    real_name       TEXT,
    persona_type    TEXT NOT NULL CHECK (persona_type IN ('real','fictional-character','alter-ego','collaborative-pseudonym')),
    bio             TEXT,
    age_range       TEXT,
    location        TEXT,
    photo_path      TEXT,
    social_json     TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    archived_at     TEXT
);

CREATE INDEX idx_artists_slug ON artists(slug);

-- ============================================================================
-- 2. albums — the project container
-- ============================================================================

CREATE TABLE albums (
    id              TEXT PRIMARY KEY,
    slug            TEXT NOT NULL UNIQUE,
    artist_id       TEXT NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    concept         TEXT NOT NULL,
    scope           TEXT NOT NULL CHECK (scope IN ('single','ep','album','double-feature','concept-piece')),
    genre_primary   TEXT,
    genre_secondary TEXT,
    runtime_target  TEXT NOT NULL CHECK (runtime_target IN ('radio-edit','standard','extended','immersive')),
    motif           TEXT,
    production      TEXT CHECK (production IS NULL OR production IN ('stripped','full-band','electronic','cinematic','hybrid')),
    lyrical_source  TEXT CHECK (lyrical_source IS NULL OR lyrical_source IN ('user-writes','agent-writes','co-write')),
    distribution    TEXT CHECK (distribution IS NULL OR distribution IN ('just-for-me','routenote-free','full-dsp','physical-and-dsp')),
    explicit        INTEGER NOT NULL DEFAULT 0 CHECK (explicit IN (0,1,2)),
    mastering_target TEXT,
    deadline        TEXT,
    status          TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','active','paused','done','archived','finalized')),
    cover_art_path  TEXT,
    cassette_sticker_path TEXT,
    press_kit_path  TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    finalized_at    TEXT,
    archived_at     TEXT
);

CREATE INDEX idx_albums_artist ON albums(artist_id);
CREATE INDEX idx_albums_status ON albums(status);

-- ============================================================================
-- 3. album_sessions — per-album session state (Q27 first-class)
-- ============================================================================

CREATE TABLE album_sessions (
    id              TEXT PRIMARY KEY,
    album_id        TEXT NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','paused','done','archived')),
    started_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    last_activity_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    paused_at       TEXT,
    resumed_at      TEXT,
    completed_at    TEXT,
    auto_paused     INTEGER NOT NULL DEFAULT 0,
    auto_pause_reason TEXT,
    notes           TEXT
);

CREATE INDEX idx_sessions_album ON album_sessions(album_id);
CREATE INDEX idx_sessions_status ON album_sessions(status);

-- Ironclad single-active-session-per-album (Q29f)
CREATE UNIQUE INDEX uniq_album_active
    ON album_sessions(album_id)
    WHERE status = 'active';

-- ============================================================================
-- 4. tracks — individual songs
-- ============================================================================

CREATE TABLE tracks (
    id              TEXT PRIMARY KEY,
    album_id        TEXT NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    session_id      TEXT REFERENCES album_sessions(id) ON DELETE SET NULL,
    track_index     INTEGER NOT NULL CHECK (track_index BETWEEN 1 AND 12),
    title           TEXT NOT NULL,
    theme           TEXT,
    mood            TEXT,
    bpm_target      INTEGER,
    key_target      TEXT,
    duration_target_s REAL,
    duration_actual_s REAL,
    audio_path      TEXT,
    lyrics_path     TEXT,
    lyrics_quality_score INTEGER,
    vocals_text     TEXT,
    lyrics_optimizer_used INTEGER NOT NULL DEFAULT 0,
    is_instrumental INTEGER NOT NULL DEFAULT 0,
    lyrics_text     TEXT,
    generation_params_json TEXT,
    generation_response_json TEXT,
    mastered_path   TEXT,
    id3_metadata_json TEXT,
    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','generated','approved','mastered','failed')),
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (album_id, track_index)
);

CREATE INDEX idx_tracks_album ON tracks(album_id);
CREATE INDEX idx_tracks_session ON tracks(session_id);
CREATE INDEX idx_tracks_status ON tracks(status);

-- ============================================================================
-- 5. lyrics_drafts — pre-finalize iterations
-- ============================================================================

CREATE TABLE lyrics_drafts (
    id              TEXT PRIMARY KEY,
    track_id        TEXT NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    version         INTEGER NOT NULL,
    lyrics_text     TEXT NOT NULL,
    quality_score   INTEGER,
    author          TEXT NOT NULL CHECK (author IN ('user','agent','co-write')),
    is_current      INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (track_id, version)
);

CREATE INDEX idx_lyrics_track ON lyrics_drafts(track_id);

-- Only one current per track (table-level uniqueness via index)
CREATE UNIQUE INDEX uniq_lyrics_current
    ON lyrics_drafts(track_id)
    WHERE is_current = 1;

-- ============================================================================
-- 6. events — unified activity log
-- ============================================================================

CREATE TABLE events (
    id              TEXT PRIMARY KEY,
    session_id      TEXT REFERENCES album_sessions(id) ON DELETE CASCADE,
    album_id        TEXT NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,
    actor           TEXT NOT NULL CHECK (actor IN ('user','agent','system','cli','daemon')),
    payload_json    TEXT,
    layer_id        TEXT,
    decision_id     TEXT REFERENCES decisions(id),
    build_job_id    TEXT REFERENCES build_jobs(id),
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE INDEX idx_events_session ON events(session_id, created_at);
CREATE INDEX idx_events_album ON events(album_id, created_at);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_layer ON events(layer_id);

-- ============================================================================
-- 7. decisions — locked user choices (Q31 + Q36)
-- ============================================================================

CREATE TABLE decisions (
    id              TEXT PRIMARY KEY,
    session_id      TEXT REFERENCES album_sessions(id) ON DELETE CASCADE,
    album_id        TEXT NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    layer_id        TEXT NOT NULL,
    decision_type   TEXT NOT NULL,
    summary         TEXT NOT NULL,
    payload_json    TEXT,
    is_locked       INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE INDEX idx_decisions_album ON decisions(album_id);
CREATE INDEX idx_decisions_layer ON decisions(layer_id);

-- ============================================================================
-- 8. api_prompts + api_responses — full audit trail (Q1.1.d)
-- ============================================================================

CREATE TABLE api_prompts (
    id              TEXT PRIMARY KEY,
    session_id      TEXT REFERENCES album_sessions(id) ON DELETE CASCADE,
    album_id        TEXT NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    action          TEXT NOT NULL,
    layer_id        TEXT,
    request_json    TEXT NOT NULL,
    build_job_id    TEXT REFERENCES build_jobs(id),
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE INDEX idx_prompts_album ON api_prompts(album_id);
CREATE INDEX idx_prompts_action ON api_prompts(action);

CREATE TABLE api_responses (
    id              TEXT PRIMARY KEY,
    prompt_id       TEXT NOT NULL REFERENCES api_prompts(id) ON DELETE CASCADE,
    trace_id        TEXT,
    response_json   TEXT NOT NULL,
    audio_url       TEXT,
    audio_local_path TEXT,
    duration_ms     INTEGER,
    size_bytes      INTEGER,
    rc              INTEGER,
    error_message   TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE INDEX idx_responses_prompt ON api_responses(prompt_id);

-- ============================================================================
-- 9. pipeline_state — current 12-layer status per album
-- ============================================================================

CREATE TABLE pipeline_state (
    id              TEXT PRIMARY KEY,
    album_id        TEXT NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    layer_id        TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('pending','in_progress','awaiting_approval','approved','done','skipped','failed')),
    started_at      TEXT,
    approved_at     TEXT,
    completed_at    TEXT,
    failure_count   INTEGER NOT NULL DEFAULT 0,
    UNIQUE (album_id, layer_id)
);

CREATE INDEX idx_pipeline_album ON pipeline_state(album_id);
CREATE INDEX idx_pipeline_status ON pipeline_state(status);

-- ============================================================================
-- 10. build_jobs — the queue (Q29, Q29a, Q29b, Q29d)
-- ============================================================================

CREATE TABLE build_jobs (
    id              TEXT PRIMARY KEY,
    session_id      TEXT REFERENCES album_sessions(id) ON DELETE CASCADE,
    album_id        TEXT NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    layer_id        TEXT NOT NULL,
    action          TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','succeeded','failed','orphaned','cancelled')),
    pid             INTEGER,
    heartbeat_at    TEXT,
    attempt_count   INTEGER NOT NULL DEFAULT 0,
    payload_json    TEXT,
    error_message   TEXT,
    queued_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    started_at      TEXT,
    completed_at    TEXT
);

CREATE INDEX idx_jobs_status ON build_jobs(status);
CREATE INDEX idx_jobs_album ON build_jobs(album_id);

-- ============================================================================
-- 11. assets — versions of media files (Q30)
-- ============================================================================

CREATE TABLE assets (
    id              TEXT PRIMARY KEY,
    album_id        TEXT NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    asset_type      TEXT NOT NULL,
    variant_name    TEXT,
    file_path       TEXT NOT NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    is_current      INTEGER NOT NULL DEFAULT 0,
    is_in_old       INTEGER NOT NULL DEFAULT 0,
    sha256          TEXT NOT NULL,
    file_size       INTEGER,
    generation_params_json TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    moved_to_old_at TEXT,
    UNIQUE (album_id, asset_type, variant_name, version)
);

CREATE INDEX idx_assets_album ON assets(album_id);
CREATE INDEX idx_assets_current ON assets(album_id, asset_type, is_current);

-- ============================================================================
-- 12. intake_briefs — saved intake submissions
-- ============================================================================

CREATE TABLE intake_briefs (
    id              TEXT PRIMARY KEY,
    album_id        TEXT NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    schema_version  TEXT NOT NULL,
    intake_form_version TEXT,
    answers_json    TEXT NOT NULL,
    defaults_json   TEXT,
    skipped_json    TEXT,
    submitted_at    TEXT NOT NULL,
    concept_brief_path TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE INDEX idx_intake_album ON intake_briefs(album_id);

-- ============================================================================
-- 13. quota_snapshots — for the dashboard quota chart
-- ============================================================================

CREATE TABLE quota_snapshots (
    id              TEXT PRIMARY KEY,
    model_name      TEXT NOT NULL,
    interval_remaining_pct REAL,
    weekly_remaining_pct REAL,
    interval_remaining_ms INTEGER,
    snapshot_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE INDEX idx_quota_model ON quota_snapshots(model_name, snapshot_at);

-- ============================================================================
-- TRIGGERS — derived columns
-- ============================================================================

-- albums.status reflects highest-priority active session (Q27)
-- Fires on both INSERT (new session) and UPDATE (status change).
CREATE TRIGGER trg_albums_status_insert
    AFTER INSERT ON album_sessions
BEGIN
    UPDATE albums SET status = (
        SELECT CASE
            WHEN EXISTS (SELECT 1 FROM album_sessions WHERE album_id = NEW.album_id AND status = 'active')
                THEN 'active'
            WHEN EXISTS (SELECT 1 FROM album_sessions WHERE album_id = NEW.album_id AND status = 'paused')
                THEN 'paused'
            WHEN EXISTS (SELECT 1 FROM album_sessions WHERE album_id = NEW.album_id AND status = 'done')
                THEN 'done'
            ELSE albums.status
        END
    )
    WHERE id = NEW.album_id;
END;

CREATE TRIGGER trg_albums_status_update
    AFTER UPDATE OF status ON album_sessions
    WHEN NEW.album_id IS NOT NULL
BEGIN
    UPDATE albums SET status = (
        SELECT CASE
            WHEN EXISTS (SELECT 1 FROM album_sessions WHERE album_id = NEW.album_id AND status = 'active')
                THEN 'active'
            WHEN EXISTS (SELECT 1 FROM album_sessions WHERE album_id = NEW.album_id AND status = 'paused')
                THEN 'paused'
            WHEN EXISTS (SELECT 1 FROM album_sessions WHERE album_id = NEW.album_id AND status = 'done')
                THEN 'done'
            ELSE albums.status
        END
    )
    WHERE id = NEW.album_id;
END;

-- assets.is_current — only one current per (album, asset_type, variant_name)
CREATE TRIGGER trg_assets_single_current
    AFTER UPDATE OF is_current ON assets
    WHEN NEW.is_current = 1
BEGIN
    UPDATE assets
    SET is_current = 0
    WHERE album_id = NEW.album_id
      AND asset_type = NEW.asset_type
      AND id != NEW.id
      AND (
        (variant_name IS NULL AND NEW.variant_name IS NULL)
        OR variant_name = NEW.variant_name
      )
      AND is_current = 1;
END;

-- album_sessions.last_activity_at updated on any event
CREATE TRIGGER trg_sessions_touch
    AFTER INSERT ON events
    WHEN NEW.session_id IS NOT NULL
BEGIN
    UPDATE album_sessions
    SET last_activity_at = NEW.created_at
    WHERE id = NEW.session_id
      AND status = 'active';
END;

-- ============================================================================
-- END
-- ============================================================================