"""tests/test_build_jobs.py — tests for db/build_jobs.py."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db import open_db, close_db, run_migrations
from db.build_jobs import (
    queue_job, mark_running, mark_succeeded, mark_failed,
    get_job, get_job_by_id, list_jobs, recover_orphans,
    count_jobs_by_status, max_attempts_for_layer,
)
from db.albums import create_artist, create_album


def _fresh_db():
    from db.connection import close_all
    close_all()
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    result = run_migrations(path)
    assert len(result["errors"]) == 0
    return path


def _cleanup(path):
    from db.connection import close_all
    close_all()
    for ext in ["", "-journal", "-wal", "-shm"]:
        p = Path(path + ext)
        if p.exists():
            try:
                p.unlink()
            except OSError:
                pass


def _setup_album(db):
    create_artist("a1", "Artist", db_path=db)
    create_album("a1", "Album", "a1", db_path=db)


class TestBuildJobs(unittest.TestCase):
    def setUp(self):
        self.db = _fresh_db()
        _setup_album(self.db)

    def tearDown(self):
        _cleanup(self.db)

    def test_queue_job(self):
        j = queue_job("a1", "02_lyrics_drafts", db_path=self.db)
        self.assertIsNotNone(j["id"])
        self.assertEqual(j["status"], "todo")
        self.assertEqual(j["album_id"], "a1")
        self.assertEqual(j["layer_id"], "02_lyrics_drafts")
        self.assertEqual(j["attempts"], 0)

    def test_queue_invalid_layer_raises(self):
        with self.assertRaises(ValueError):
            queue_job("a1", "99_unknown", db_path=self.db)

    def test_queue_idempotent(self):
        j1 = queue_job("a1", "02_lyrics_drafts", db_path=self.db)
        j2 = queue_job("a1", "02_lyrics_drafts", db_path=self.db)
        # Should return the same row (not create a duplicate)
        self.assertEqual(j1["id"], j2["id"])

    def test_full_lifecycle(self):
        j = queue_job("a1", "02_lyrics_drafts", db_path=self.db)
        # todo -> running
        running = mark_running(j["id"], db_path=self.db)
        self.assertEqual(running["status"], "running")
        self.assertIsNotNone(running["started_at"])
        # running -> done
        done = mark_succeeded(j["id"], db_path=self.db)
        self.assertEqual(done["status"], "done")
        self.assertIsNotNone(done["completed_at"])

    def test_mark_failed_blocks(self):
        j = queue_job("a1", "02_lyrics_drafts", db_path=self.db)
        mark_running(j["id"], db_path=self.db)
        failed = mark_failed(j["id"], "API rate limit", db_path=self.db)
        self.assertEqual(failed["status"], "blocked")
        self.assertIn("rate limit", failed["error"])
        self.assertEqual(failed["attempts"], 1)

    def test_get_job(self):
        j = queue_job("a1", "03_lyrics_finalize", db_path=self.db)
        fetched = get_job("a1", "03_lyrics_finalize", db_path=self.db)
        self.assertEqual(fetched["id"], j["id"])

    def test_list_jobs_filter(self):
        queue_job("a1", "02_lyrics_drafts", db_path=self.db)
        queue_job("a1", "03_lyrics_finalize", db_path=self.db)
        queue_job("a1", "04_vocal_recordings", db_path=self.db)
        all_jobs = list_jobs(db_path=self.db)
        self.assertEqual(len(all_jobs), 3)
        a1_jobs = list_jobs(album_id="a1", db_path=self.db)
        self.assertEqual(len(a1_jobs), 3)

    def test_count_jobs_by_status(self):
        j1 = queue_job("a1", "02_lyrics_drafts", db_path=self.db)
        queue_job("a1", "03_lyrics_finalize", db_path=self.db)
        mark_running(j1["id"], db_path=self.db)
        mark_succeeded(j1["id"], db_path=self.db)
        counts = count_jobs_by_status(album_id="a1", db_path=self.db)
        self.assertEqual(counts.get("done", 0), 1)
        self.assertEqual(counts.get("todo", 0), 1)

    def test_max_attempts_for_layer(self):
        # Expensive layers get 5 attempts
        self.assertEqual(max_attempts_for_layer("05_instrumental"), 5)
        self.assertEqual(max_attempts_for_layer("06_cover_art"), 5)
        # Cheap layers get 3
        self.assertEqual(max_attempts_for_layer("01_brief"), 3)
        self.assertEqual(max_attempts_for_layer("02_lyrics_drafts"), 3)


class TestRecoverOrphans(unittest.TestCase):
    def setUp(self):
        self.db = _fresh_db()
        _setup_album(self.db)

    def tearDown(self):
        _cleanup(self.db)

    def test_recover_orphans_marks_dead_pids(self):
        """On daemon startup: walking running jobs with stale started_at → mark 'crashed'."""
        import time
        j = queue_job("a1", "02_lyrics_drafts", db_path=self.db)
        mark_running(j["id"], db_path=self.db)
        # Backdate started_at to >5 minutes ago so the 5-min heuristic fires
        conn = open_db(self.db)
        six_minutes_ago = time.strftime("%Y-%m-%d %H:%M:%S",
                                        time.gmtime(time.time() - 360))
        conn.execute("UPDATE build_jobs SET started_at = ? WHERE id = ?",
                     (six_minutes_ago, j["id"]))
        conn.commit()
        # recover_orphans with no known_pids → assumes fresh daemon, marks all crashed
        crashed = recover_orphans(db_path=self.db)
        self.assertEqual(len(crashed), 1)
        self.assertEqual(crashed[0]["status"], "crashed")

    def test_recover_orphans_no_false_positives(self):
        """Live PIDs are NOT marked crashed."""
        j = queue_job("a1", "02_lyrics_drafts", db_path=self.db)
        # Use os.getpid() — the current Python process is definitely alive
        mark_running(j["id"], db_path=self.db)
        crashed = recover_orphans(db_path=self.db)
        self.assertEqual(len(crashed), 0)
        # The job is still running
        fetched = get_job_by_id(j["id"], db_path=self.db)
        self.assertEqual(fetched["status"], "running")


if __name__ == "__main__":
    unittest.main()
