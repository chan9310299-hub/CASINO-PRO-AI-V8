import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

APP_DIR = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP_DIR))

from database import Database, RUNTIME_DB_WARNING


class DatabaseResilienceTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "test.db")
        self._patches = [
            mock.patch("config.DB_PATH", Path(self.db_path)),
            mock.patch("database.DB_PATH", Path(self.db_path)),
            mock.patch("database.resolve_database_url", return_value=None),
        ]
        for p in self._patches:
            p.start()
        self.db = Database(force_sqlite=True)

    def tearDown(self):
        self.db.close()
        for p in self._patches:
            p.stop()
        self._tmpdir.cleanup()

    def test_get_unresolved_prediction_on_programming_error(self):
        with mock.patch.object(
            self.db, "query_one", side_effect=sqlite3.ProgrammingError("no transaction")
        ):
            self.assertIsNone(self.db.get_unresolved_prediction())
            self.assertEqual(self.db.runtime_error, RUNTIME_DB_WARNING)

    def test_get_unresolved_predictions_on_error_returns_empty(self):
        with mock.patch.object(
            self.db, "get_unresolved_prediction", side_effect=Exception("fail")
        ):
            self.assertEqual(self.db.get_unresolved_predictions(), [])

    def test_update_prediction_actual_on_programming_error(self):
        with mock.patch.object(
            self.db, "execute", return_value=None
        ):
            self.assertEqual(self.db.update_prediction_actual(1, "P", 1), 0)

    def test_undo_last_returns_false_on_programming_error(self):
        self.db.record_hand("P")
        with mock.patch.object(
            self.db, "execute", side_effect=sqlite3.ProgrammingError("rollback")
        ):
            self.assertFalse(self.db.undo_last())
            self.assertEqual(self.db.runtime_error, RUNTIME_DB_WARNING)

    def test_connection_swallows_programming_error(self):
        self.db.conn.execute("BEGIN")
        try:
            with self.db._connection():
                raise sqlite3.ProgrammingError("bad state")
        except sqlite3.ProgrammingError:
            self.fail("ProgrammingError should not propagate from _connection")
        self.assertEqual(self.db.runtime_error, RUNTIME_DB_WARNING)

    def test_get_db_status_shows_postgresql_when_url_configured(self):
        with mock.patch("database.resolve_database_url", return_value="postgresql://u:p@h/db"):
            with mock.patch("database._connect_postgresql", side_effect=Exception("fail")):
                db = Database()
                status = db.get_db_status()
                self.assertEqual(status["db_engine"], "PostgreSQL")
                self.assertTrue(status["cloud_configured"])
                db.close()

    def test_consume_runtime_error_clears_message(self):
        self.db._set_runtime_error()
        self.assertEqual(self.db.consume_runtime_error(), RUNTIME_DB_WARNING)
        self.assertIsNone(self.db.runtime_error)


if __name__ == "__main__":
    unittest.main()
