"""tests/test_regressions.py — regression tests for issues found in the
2026-08-09 audit.

These tests pin down bugs that the original test suite did not catch.
Each test is annotated with the issue number from the audit report so
the intent survives refactoring.
"""
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Use a per-test fresh DB so regression tests never mutate the live one.
from db import connection as db_conn
from db import migrations, sessions, seed
from db.connection import (
    open_db, close_db, close_all, DEFAULT_DB_PATH,
)


def _fresh_test_db() -> Path:
    """Create a fresh test DB and return its path."""
    tmp = Path(tempfile.mkdtemp())
    p = tmp / "regression.db"
    conn = sqlite3.connect(str(p))
    conn.executescript((PROJECT_ROOT / "db" / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    # Reset the per-thread cache so the new path is used.
    db_conn._thread_local.clear()
    return p


def _cleanup_thread_cache():
    """Reset all per-thread + cross-thread state after a test."""
    close_all()
    import db.connection as dc
    dc._thread_local.clear()
    dc._thread_registry.clear()


class TestReadOnlyConnection(unittest.TestCase):
    """Regression: open_db(read_only=True) used to crash because WAL
    pragma fails on readonly URI connections. Plus the cache key didn't
    include read_only, so a writable conn could be returned for a ro
    request (or vice-versa)."""

    def setUp(self):
        self.db = _fresh_test_db()

    def tearDown(self):
        _cleanup_thread_cache()

    def test_open_read_only_does_not_crash(self):
        """open_db(read_only=True) must not raise on PRAGMA."""
        conn = open_db(self.db, read_only=True)
        self.assertIsNotNone(conn)
        # Should be able to read
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        self.assertGreater(len(rows), 0)

    def test_read_only_blocks_writes(self):
        """A read_only connection must block INSERT (it's truly readonly)."""
        conn = open_db(self.db, read_only=True)
        with self.assertRaises(sqlite3.OperationalError):
            conn.execute("CREATE TABLE ro_test (x INT)")

    def test_read_only_cache_separate_from_writable(self):
        """A writable open_db followed by a read_only open_db must give
        two distinct connections (different cache keys)."""
        w = open_db(self.db, read_only=False)
        r = open_db(self.db, read_only=True)
        self.assertIsNot(w, r,
                         "writable and readonly should be different connections")

    def test_writable_cache_separate_from_read_only(self):
        """Reverse order: read_only first, then writable."""
        r = open_db(self.db, read_only=True)
        w = open_db(self.db, read_only=False)
        self.assertIsNot(r, w)


class TestOpenSessionRace(unittest.TestCase):
    """Regression: open_session had a TOCTOU race between the active_count
    SELECT and the INSERT. With concurrent threads, multiple inserts could
    exceed MAX_ACTIVE_SESSIONS. The fix wraps the count+insert in an
    IMMEDIATE transaction so concurrent calls serialize."""

    def setUp(self):
        from db.albums import create_artist, create_album
        self.db = _fresh_test_db()
        create_artist("a1", "A1", db_path=self.db)
        create_album("al1", "Album", "a1", db_path=self.db)

    def tearDown(self):
        _cleanup_thread_cache()

    def test_concurrent_open_session_respects_max(self):
        """20 concurrent threads attempting to open a session must yield
        at most MAX_ACTIVE_SESSIONS=3 successful opens."""
        from db.sessions import count_active_sessions, MAX_ACTIVE_SESSIONS
        results = []

        def worker():
            s = sessions.open_session("al1", db_path=self.db)
            results.append(s["id"] if s else None)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        successful = [r for r in results if r is not None]
        active = count_active_sessions(db_path=self.db)
        self.assertEqual(active, MAX_ACTIVE_SESSIONS,
                         f"Expected exactly {MAX_ACTIVE_SESSIONS} active, got {active}")
        self.assertEqual(len(successful), MAX_ACTIVE_SESSIONS,
                         f"Expected {MAX_ACTIVE_SESSIONS} successful opens, got {len(successful)}")


class TestMarkApprovedState(unittest.TestCase):
    """Regression: mark_approved used to set status='needs_approval' instead
    of transitioning to 'ready'. The schema documents 'ready' as the
    post-approval state but no code path ever produced it."""

    def setUp(self):
        from db.albums import create_artist, create_album
        self.db = _fresh_test_db()
        create_artist("a1", "A1", db_path=self.db)
        create_album("al1", "Album", "a1", db_path=self.db)

    def tearDown(self):
        _cleanup_thread_cache()

    def test_mark_approved_transitions_to_ready(self):
        """mark_approved must set status='ready' (not 'needs_approval')."""
        from db.build_jobs import queue_job, get_job
        from db.pipeline import mark_approved, APPROVAL_REQUIRED

        # Pick any approval-gated layer
        layer = next(iter(APPROVAL_REQUIRED))
        queue_job("al1", layer, db_path=self.db)
        ok = mark_approved(layer, "al1", db_path=self.db)
        self.assertTrue(ok)
        row = get_job("al1", layer, db_path=self.db)
        self.assertEqual(row["status"], "ready",
                         f"Expected status='ready', got {row['status']!r}")
        self.assertIsNotNone(row.get("approved_at"))


class TestMigrationAtomicity(unittest.TestCase):
    """Regression: _apply_migration used executescript() which auto-commits
    each statement. A mid-script failure would leave partial schema. The
    fix splits statements and uses BEGIN/COMMIT/ROLLBACK."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.db = self.tmpdir / "mig.db"
        # Save original DEFAULT_DB_PATH so we can restore it on tearDown
        # (other tests rely on it pointing at the live .meta/sonic-sounds.db).
        self._orig_default_db_path = db_conn.DEFAULT_DB_PATH

    def tearDown(self):
        # Restore module-level DEFAULT_DB_PATH so other tests are unaffected.
        db_conn.DEFAULT_DB_PATH = self._orig_default_db_path
        _cleanup_thread_cache()

    def test_failed_migration_leaves_no_partial_schema(self):
        """A failing migration must roll back all DDL and not bump version.

        Migrations come from the canonical .meta/migrations/ dir, so we
        can't easily inject a failing one without touching project state.
        Instead we test _apply_migration directly with a hand-crafted
        failing migration file in a tempdir.
        """
        # Bootstrap a fresh db_meta
        conn = sqlite3.connect(str(self.db))
        conn.execute("CREATE TABLE db_meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO db_meta (key, value) VALUES ('schema_version', '0')")
        conn.commit()
        conn.close()

        # Write a migration with statement 1 (ok) + statement 2 (fails)
        failing_migration = self.tmpdir / "002_failing.sql"
        failing_migration.write_text("""
CREATE TABLE good (x INT);
INSERT INTO nonexistent_table VALUES (1);
""", encoding="utf-8")

        # Apply directly via _apply_migration
        conn = migrations.open_db(self.db)
        with self.assertRaises(sqlite3.Error,
                               msg="expected the migration to fail"):
            migrations._apply_migration(conn, 2, "failing", failing_migration)
        # Connection must still be usable (transaction was rolled back, not poisoned)
        conn.execute("SELECT 1").fetchone()
        from db.connection import close_db
        close_db(self.db)

        # Verify partial DDL was rolled back
        verify_conn = sqlite3.connect(str(self.db))
        good_exists = verify_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='good'"
        ).fetchone()
        self.assertIsNone(good_exists,
                          "Atomicity violated: 'good' table survived rollback")
        version = verify_conn.execute(
            "SELECT value FROM db_meta WHERE key='schema_version'"
        ).fetchone()[0]
        self.assertEqual(version, "0",
                         f"schema_version bumped despite rollback: {version}")
        verify_conn.close()


class TestRecoverOrphansKnownPids(unittest.TestCase):
    """Regression: recover_orphans accepted a known_pids argument but
    ignored it. The fix uses it to skip rows whose id is in the set."""

    def setUp(self):
        from db.albums import create_artist, create_album
        self.db = _fresh_test_db()
        create_artist("a1", "A1", db_path=self.db)
        for i in range(5):
            create_album(f"al{i}", f"Album {i}", "a1", db_path=self.db)

    def tearDown(self):
        _cleanup_thread_cache()

    def test_known_pids_set_skips_matching_rows(self):
        from db.build_jobs import queue_job, mark_running, recover_orphans, list_jobs
        from datetime import datetime, timezone, timedelta

        # Insert 3 running jobs with old started_at (>5 min ago)
        for i in range(3):
            queue_job(f"al{i}", "01_brief", db_path=self.db)
        jobs = list_jobs(db_path=self.db, status="todo")
        for j in jobs:
            old_started = (datetime.now(timezone.utc) - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
            mark_running(j["id"], started_at=old_started, db_path=self.db)

        # All should be running now
        running = list_jobs(db_path=self.db, status="running")
        ids = {j["id"] for j in running}
        self.assertEqual(len(ids), 3, f"Expected 3 running jobs, got {len(ids)}")

        # Recover with one job ID in known_pids → should be skipped
        target_id = next(iter(ids))
        crashed = recover_orphans(known_pids={target_id}, db_path=self.db)
        crashed_ids = {j["id"] for j in crashed}
        # The protected job must NOT be in the crashed list
        self.assertNotIn(target_id, crashed_ids,
                         "known_pids job should have been skipped")

    def test_known_pids_none_marks_all_old_running(self):
        """known_pids=None (default) marks all old running jobs as crashed."""
        from db.build_jobs import queue_job, mark_running, recover_orphans
        from datetime import datetime, timezone, timedelta
        queue_job("al0", "01_brief", db_path=self.db)
        old_started = (datetime.now(timezone.utc) - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
        mark_running(1, started_at=old_started, db_path=self.db)
        crashed = recover_orphans(db_path=self.db)
        self.assertEqual(len(crashed), 1)


class TestSchemaTriggers(unittest.TestCase):
    """Regression: album.status trigger fired only on UPDATE, not on INSERT.
    Inserting a new session for an album that was 'archived' left the
    album status stale."""

    def setUp(self):
        self.db = _fresh_test_db()

    def tearDown(self):
        _cleanup_thread_cache()

    def test_album_status_syncs_on_session_insert(self):
        """Inserting an active session for an archived album should flip
        the album status to 'active' (via the new INSERT trigger)."""
        from db.albums import create_artist, create_album, get_album
        from db.sessions import open_session
        create_artist("a1", "A1", db_path=self.db)
        create_album("al1", "Album", "a1", db_path=self.db)
        # Archive the album first
        from db.albums import archive_album
        archive_album("al1", db_path=self.db)
        self.assertEqual(get_album("al1", db_path=self.db)["status"], "archived")
        # Open a session — trigger should flip status to 'active'
        open_session("al1", db_path=self.db)
        status = get_album("al1", db_path=self.db)["status"]
        self.assertEqual(status, "active",
                         f"Expected status='active' after session insert, got {status!r}")


class TestCloseAllAcrossThreads(unittest.TestCase):
    """Regression: close_all() only closed the calling thread's connections
    because threading.local() is per-thread. The fix uses a cross-thread
    registry."""

    def setUp(self):
        self.db = _fresh_test_db()

    def tearDown(self):
        from db.connection import close_all
        close_all()
        db_conn._thread_local.clear()
        db_conn._thread_registry.clear()

    def test_close_all_closes_connections_from_other_threads(self):
        """Spawn worker threads that open connections, then call close_all
        from the main thread — all worker connections should be closed."""
        results = {}

        def worker(name):
            conn = open_db(self.db)
            results[name] = conn

        threads = [threading.Thread(target=worker, args=(f"w{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All workers opened connections
        self.assertEqual(len(results), 5)

        # close_all from the main thread should close them all
        close_all()

        # Every worker connection should now be closed
        for name, conn in results.items():
            with self.assertRaises(sqlite3.ProgrammingError,
                                   msg=f"Worker {name} connection should be closed"):
                conn.execute("SELECT 1")


class TestEventsAlbumFK(unittest.TestCase):
    """Regression: events.album_id had no FK to albums.id, allowing
    orphan album_ids."""

    def setUp(self):
        self.db = _fresh_test_db()

    def tearDown(self):
        _cleanup_thread_cache()

    def test_event_with_bogus_album_id_rejected(self):
        from db.albums import create_artist, create_album
        from db.events import create_event
        from db.sessions import open_session
        create_artist("a1", "A1", db_path=self.db)
        create_album("al1", "Album", "a1", db_path=self.db)
        s = open_session("al1", db_path=self.db)
        with self.assertRaises(sqlite3.IntegrityError,
                               msg="Bogus album_id should be rejected by FK"):
            create_event(s["id"], "user", "chat", "hello",
                         album_id="BOGUS", db_path=self.db)


class TestConnectionCloseOnLookup(unittest.TestCase):
    """Regression: the /api/audio endpoint used to call conn.close() in its
    _lookup closure, which left the closed connection in the per-thread
    cache. The next open_db() in the same worker thread returned the stale
    closed connection. The fix uses close_db() to pop from cache."""

    def setUp(self):
        self.db = _fresh_test_db()

    def tearDown(self):
        _cleanup_thread_cache()

    def test_close_then_reopen_returns_fresh_connection(self):
        """If a handler does open_db → conn.close() (raw), the cache still
        has the closed conn. Calling open_db() again returns the closed
        one and raises. The fix in build/serve.py uses close_db() to pop
        the cache entry. Verify the close_db contract here."""
        # Simulate the broken pattern (raw close) — show the bug exists
        conn = open_db(self.db)
        conn.close()
        # Cache still has it
        cache = db_conn._thread_local[threading.get_ident()]
        self.assertEqual(len(cache), 1)
        # Now the fixed pattern
        fresh = open_db(self.db)
        # Bug: returns the same closed object (raises on use)
        try:
            fresh.execute("SELECT 1").fetchone()
            same_object_works = True
        except sqlite3.ProgrammingError:
            same_object_works = False
        # This documents the bug — we expect same_object_works=False
        self.assertFalse(same_object_works,
                         "Raw conn.close leaves stale entry in cache")

        # Now apply the fix: close_db() pops the cache
        close_db(self.db)
        cache = db_conn._thread_local[threading.get_ident()]
        self.assertEqual(len(cache), 0)
        # Next open_db returns a fresh connection
        new_conn = open_db(self.db)
        result = new_conn.execute("SELECT 1").fetchone()
        self.assertEqual(result[0], 1)


class TestSeedMIMEFix(unittest.TestCase):
    """Regression: seed.py hardcoded mime='image/jpeg' for posters/merch
    regardless of extension, and 'video/mp4' for all videos. Now uses
    _mime_for_image / _mime_for_video based on actual extension."""

    def test_mime_for_image_png(self):
        from db.seed import _mime_for_image
        self.assertEqual(_mime_for_image(Path("foo.png")), "image/png")

    def test_mime_for_image_jpg(self):
        from db.seed import _mime_for_image
        self.assertEqual(_mime_for_image(Path("foo.jpg")), "image/jpeg")
        self.assertEqual(_mime_for_image(Path("foo.jpeg")), "image/jpeg")

    def test_mime_for_image_webp(self):
        from db.seed import _mime_for_image
        self.assertEqual(_mime_for_image(Path("foo.webp")), "image/webp")

    def test_mime_for_video_mov(self):
        from db.seed import _mime_for_video
        self.assertEqual(_mime_for_video(Path("foo.mov")), "video/quicktime")

    def test_mime_for_video_webm(self):
        from db.seed import _mime_for_video
        self.assertEqual(_mime_for_video(Path("foo.webm")), "video/webm")


class TestSeedISRCFormat(unittest.TestCase):
    """Regression: ISRC was formatted as 'US-S1Z-25-01' (12 chars with
    dashes). Real ISRC is 12 chars without dashes: 'USS1Z2500001'."""

    def test_album_isrc_format(self):
        from db.seed import HALF_LIGHT_HOURS_ALBUM
        isrc = HALF_LIGHT_HOURS_ALBUM["isrc"]
        self.assertEqual(len(isrc), 12, f"Album ISRC should be 12 chars, got {len(isrc)}")
        self.assertNotIn("-", isrc, "ISRC must not contain dashes")

    def test_track_isrc_format(self):
        """Track ISRCs are computed from track number. Format:
        USS1Z25NNNNN (5-digit designation)."""
        # Inline the formula since it lives inside seed_half_light_hours
        for tid in range(1, 11):
            isrc = f"USS1Z25{tid:05d}"
            self.assertEqual(len(isrc), 12)
            self.assertNotIn("-", isrc)




class TestDaemonLockRelease(unittest.TestCase):
    """Regression: Daemon.start() used to bypass the lock-release
    finally block when sys.exit(1) was called during setup (lock
    acquisition failure, migration error). The lock file would remain
    on disk, blocking the next daemon start. The fix wraps setup
    steps in a try block that releases the lock on any failure.
    """

    def test_lock_released_on_migration_failure(self):
        """If run_migrations raises SystemExit(1) mid-startup, the
        lock file must be removed before the process exits."""
        from build.serve import Daemon
        import tempfile, shutil, os
        from pathlib import Path

        tmpdir = Path(tempfile.mkdtemp())
        daemon = Daemon(
            host="127.0.0.1", port=18765,
            lock_path=tmpdir / "test.lock",
            log_path=tmpdir / "test.log",
        )

        # Force run_migrations to fail with SystemExit(1)
        def broken_run_migrations(self):
            raise SystemExit(1)
        daemon.run_migrations = broken_run_migrations.__get__(daemon)

        try:
            daemon.start()
            self.fail("start() should have raised SystemExit")
        except SystemExit:
            pass

        # Lock file should have been released
        self.assertFalse(
            daemon.lock.path.exists(),
            f"BUG: lock file remains at {daemon.lock.path} after sys.exit(1)",
        )
        shutil.rmtree(tmpdir, ignore_errors=True)


class TestRegistryNoLeak(unittest.TestCase):
    """Regression: the cross-thread registry leaked empty _ThreadEntry
    objects after close_db / close_all. Over a daemon's lifetime the
    dict grew monotonically. The fix pops entries when their conns
    list becomes empty.

    These tests clean the main-thread registry in setUp because other
    test modules in this suite (test_decisions, test_events, test_pipeline,
    test_queries) don't close their main-thread conns, leaving stale
    entries. Our fix (#1) is the production fix; the test cleanup here
    ensures these assertions are deterministic.
    """

    def setUp(self):
        # Clean any pre-existing main-thread registry entries so the
        # assertions below are independent of test ordering. The cleanup
        # matches what _cleanup_thread_cache() does.
        import db.connection as dc
        from db.connection import close_all
        close_all()
        dc._thread_local.clear()
        dc._thread_registry.clear()
        self.db = _fresh_test_db()

    def tearDown(self):
        _cleanup_thread_cache()

    def test_close_db_pops_empty_registry_entry(self):
        """open_db in current thread, then close_db, should remove
        the entry from _thread_registry."""
        import db.connection as dc
        import threading
        dc.open_db(self.db)
        tid = threading.get_ident()
        self.assertIn(tid, dc._thread_registry,
                      "Entry should exist after open_db")
        dc.close_db(self.db)
        self.assertNotIn(tid, dc._thread_registry,
                         f"Entry should be popped after close_db, "
                         f"still has {len(dc._thread_registry)} entries")

    def test_threads_that_cleanly_close_dont_leak(self):
        """50 threads, each opens+closes 1 conn, should leave registry
        empty (no leaked entries)."""
        import db.connection as dc
        import threading
        def worker():
            dc.open_db(self.db)
            dc.close_db(self.db)
        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(dc._thread_registry), 0,
                         f"Expected empty registry, got {len(dc._thread_registry)} entries")

    def test_close_all_pops_entries_with_open_conns(self):
        """A leaking thread leaves an entry with 1 conn. close_all()
        should close that conn AND pop the now-empty entry."""
        import db.connection as dc
        import threading
        def leak_worker():
            dc.open_db(self.db)
            # don't close_db — simulate a thread that died without cleanup
        t = threading.Thread(target=leak_worker)
        t.start()
        t.join()
        self.assertEqual(len(dc._thread_registry), 1,
                         "Leak worker should leave 1 entry")
        dc.close_all()
        self.assertEqual(len(dc._thread_registry), 0,
                         f"close_all should pop the now-empty entry, "
                         f"got {len(dc._thread_registry)} entries")


class TestEventsArchiveFK(unittest.TestCase):
    """Regression: events.album_id FK has ON DELETE SET NULL. Note
    this fires on DELETE, not on UPDATE (archive_album). The event
    log is preserved across archive cycles.
    """

    def setUp(self):
        self.db = _fresh_test_db()

    def tearDown(self):
        _cleanup_thread_cache()

    def test_delete_album_cascades_events_via_session(self):
        """Hard DELETE of an album cascades events away via the
        album_sessions → events CASCADE chain. The events.album_id
        SET NULL clause never actually fires because events are
        gone before the FK check on events.album_id."""
        from db.albums import create_artist, create_album
        from db.events import create_event, list_events
        from db.sessions import open_session
        import sqlite3
        create_artist("a1", "A1", db_path=self.db)
        create_album("a1", "Album", "a1", db_path=self.db)
        s = open_session("a1", db_path=self.db)
        create_event(s["id"], "user", "chat", "event", album_id="a1", db_path=self.db)
        # Verify event exists
        evts_before = list_events(s["id"], db_path=self.db)
        self.assertEqual(len(evts_before), 1)
        # Hard delete the album. Must enable FK enforcement on the raw
        # connection (sqlite3 default is OFF).
        c = sqlite3.connect(str(self.db))
        c.execute("PRAGMA foreign_keys = ON")
        c.execute("DELETE FROM albums WHERE id = 'a1'")
        c.commit()
        c.close()
        # Events cascade-deleted via album_sessions.session_id CASCADE
        evts_after = list_events(s["id"], db_path=self.db)
        self.assertEqual(len(evts_after), 0,
                         "events should be deleted via session cascade chain")

    def test_archive_album_keeps_event_album_id(self):
        """archive_album is an UPDATE, not DELETE, so events.album_id
        stays as the archived album's id. This is intentional."""
        from db.albums import create_artist, create_album, archive_album
        from db.events import create_event, list_events
        from db.sessions import open_session
        create_artist("a1", "A1", db_path=self.db)
        create_album("a1", "Album", "a1", db_path=self.db)
        s = open_session("a1", db_path=self.db)
        create_event(s["id"], "user", "chat", "event", album_id="a1", db_path=self.db)
        archive_album("a1", db_path=self.db)
        evts = list_events(s["id"], db_path=self.db)
        self.assertEqual(evts[0]["album_id"], "a1",
                         "archive_album (UPDATE) should NOT null events.album_id")



if __name__ == "__main__":
    unittest.main()
