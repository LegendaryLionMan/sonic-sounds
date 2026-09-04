"""tests/test_decisions.py — tests for db/decisions.py."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db import open_db, close_db, run_migrations
from db.decisions import (
    create_decision, get_decision, get_decision_by_id,
    list_decisions, update_decision, delete_decision, count_decisions,
)
from db.albums import create_artist, create_album
from db.sessions import open_session


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


class TestDecisions(unittest.TestCase):
    def setUp(self):
        self.db = _fresh_db()
        create_artist("a1", "Artist", db_path=self.db)
        create_album("a1", "Album", "a1", db_path=self.db)
        self.session = open_session("a1", db_path=self.db)

    def tearDown(self):
        _cleanup(self.db)

    def test_create_and_get_decision(self):
        d = create_decision("M01", "mandatory",
                            question="Album concept?",
                            answer="Dream-folk nostalgia",
                            rationale="Half-Light Hours, autumn vignettes",
                            source_doc="META-DECISIONS-2026-08-02",
                            album_id="a1", session_id=self.session["id"],
                            db_path=self.db)
        self.assertIsNotNone(d["id"])
        self.assertEqual(d["code"], "M01")
        self.assertEqual(d["tier"], "mandatory")
        self.assertEqual(d["answer"], "Dream-folk nostalgia")

        # Get by code
        fetched = get_decision("M01", album_id="a1", db_path=self.db)
        self.assertEqual(fetched["answer"], "Dream-folk nostalgia")

    def test_list_decisions_filter_by_tier(self):
        create_decision("M01", "mandatory", album_id="a1", db_path=self.db)
        create_decision("M02", "mandatory", album_id="a1", db_path=self.db)
        create_decision("R12", "recommended", album_id="a1", db_path=self.db)
        create_decision("E22", "extra", album_id="a1", db_path=self.db)

        all_d = list_decisions(album_id="a1", db_path=self.db)
        self.assertEqual(len(all_d), 4)

        mandatory = list_decisions(tier="mandatory", db_path=self.db)
        self.assertEqual(len(mandatory), 2)

        recommended = list_decisions(tier="recommended", db_path=self.db)
        self.assertEqual(len(recommended), 1)

    def test_update_decision(self):
        d = create_decision("M01", "mandatory", answer="first answer",
                            album_id="a1", db_path=self.db)
        updated = update_decision(d["id"], answer="revised answer",
                                  rationale="user said this in re-walk",
                                  db_path=self.db)
        self.assertEqual(updated["answer"], "revised answer")
        self.assertEqual(updated["rationale"], "user said this in re-walk")

    def test_delete_decision(self):
        d = create_decision("M01", "mandatory", album_id="a1", db_path=self.db)
        self.assertTrue(delete_decision(d["id"], db_path=self.db))
        self.assertIsNone(get_decision_by_id(d["id"], db_path=self.db))

    def test_get_decision_by_id(self):
        d = create_decision("Q21", "mandatory", answer="Mixtape '85",
                            album_id="a1", db_path=self.db)
        self.assertEqual(get_decision_by_id(d["id"], db_path=self.db)["answer"],
                         "Mixtape '85")

    def test_count_decisions(self):
        create_decision("M01", "mandatory", album_id="a1", db_path=self.db)
        create_decision("M02", "mandatory", album_id="a1", db_path=self.db)
        create_decision("R12", "recommended", album_id="a1", db_path=self.db)
        self.assertEqual(count_decisions(db_path=self.db), 3)
        self.assertEqual(count_decisions(tier="mandatory", db_path=self.db), 2)
        self.assertEqual(count_decisions(tier="recommended", db_path=self.db), 1)


if __name__ == "__main__":
    unittest.main()
