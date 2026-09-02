-- 003_events_session_nullable.sql
-- Day 6: build runner writes "global" events (build_started, build_succeeded,
-- build_failed, build_crashed) with a synthetic session_id="<build>".
-- These don't belong to any particular album session — they're per-job
-- audit events. The events.session_id column was NOT NULL with FK
-- to album_sessions(id), which made sense for chat events but blocks
-- the build runner. Make session_id nullable so global events work.

-- SQLite ALTER TABLE supports DROP NOT NULL (added in 3.35). The schema
-- comment already says "nullable (some events are global)".
PRAGMA foreign_keys = OFF;
-- Recreate events table without the NOT NULL on session_id.
CREATE TABLE events_new (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT,                       -- nullable: chat events have a real session; build events use '<build>'
    album_id        TEXT,                       -- nullable (some events are global)
    role            TEXT NOT NULL,
    kind            TEXT NOT NULL,
    content         TEXT,
    payload_json    TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES album_sessions(id) ON DELETE CASCADE
);
INSERT INTO events_new (id, session_id, album_id, role, kind, content, payload_json, created_at)
    SELECT id, session_id, album_id, role, kind, content, payload_json, created_at FROM events;
DROP TABLE events;
ALTER TABLE events_new RENAME TO events;
-- Re-create the indexes that were on events
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_events_album ON events(album_id, created_at);
PRAGMA foreign_keys = ON;
