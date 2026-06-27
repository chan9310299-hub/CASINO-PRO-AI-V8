import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

APP_DIR = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP_DIR))

from database import Database, CLOUD_DB_ERROR_MSG


class CloudNoSqliteFallbackTests(unittest.TestCase):
    def test_database_url_set_never_opens_sqlite(self):
        with mock.patch("database.resolve_database_url", return_value="postgresql://u:p@h/db"):
            with mock.patch("database._connect_postgresql", side_effect=Exception("connect fail")):
                with mock.patch("sqlite3.connect") as mock_sqlite:
                    db = Database()
                    mock_sqlite.assert_not_called()
                    self.assertEqual(db.backend, "postgresql")
                    self.assertIsNone(db.conn)
                    self.assertEqual(db.connection_error, CLOUD_DB_ERROR_MSG)

    def test_database_url_success_uses_postgres(self):
        mock_conn = mock.MagicMock()
        mock_conn.closed = False
        with mock.patch("database.resolve_database_url", return_value="postgresql://u:p@h/db"):
            with mock.patch("database._connect_postgresql", return_value=(mock_conn, "psycopg2")):
                with mock.patch.object(Database, "_bootstrap_postgres"):
                    with mock.patch("sqlite3.connect") as mock_sqlite:
                        db = Database()
                        mock_sqlite.assert_not_called()
                        self.assertTrue(db.is_postgres)
                        self.assertIsNone(db.connection_error)


class CloudAliasMethodTests(unittest.TestCase):
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

    def test_record_hand_and_save_ai_prediction(self):
        self.db.record_hand("P")
        self.assertEqual(self.db.get_results(), ["P"])
        pid = self.db.save_ai_prediction(
            1, '["P"]', "B", 0.7, "{}", "{}", '["test"]',
        )
        self.assertIsNotNone(pid)
        self.assertEqual(len(self.db.get_unresolved_predictions()), 1)

    def test_undo_last_sqlite(self):
        self.db.record_hand("P")
        self.db.record_hand("B")
        self.db.undo_last()
        self.assertEqual(self.db.get_results(), ["P"])


if __name__ == "__main__":
    unittest.main()
