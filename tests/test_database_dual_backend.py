import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

APP_DIR = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP_DIR))

from database import Database, _adapt_sql, _scalar


class DatabaseDualBackendTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "test.db")
        self._patches = [
            mock.patch("config.DB_PATH", Path(self.db_path)),
            mock.patch("database.DB_PATH", Path(self.db_path)),
            mock.patch("database.db_config.get_database_url", return_value=None),
        ]
        for p in self._patches:
            p.start()
        self.db = Database(force_sqlite=True)

    def tearDown(self):
        self.db.close()
        for p in self._patches:
            p.stop()
        self._tmpdir.cleanup()

    def test_sqlite_execute_query(self):
        self.db.execute(
            "INSERT INTO results (result, created_at) VALUES (?, ?)",
            ("P", "2026-01-01 00:00:00"),
        )
        self.db.conn.commit()
        rows = self.db.query("SELECT result FROM results ORDER BY id ASC")
        self.assertEqual(rows[0]["result"], "P")

    def test_undo_last_sqlite(self):
        self.db.add_result("P")
        self.db.add_result("B")
        self.db.undo_last()
        self.assertEqual(self.db.get_results(), ["P"])

    def test_adapt_sql_postgres(self):
        sql = "SELECT * FROM t WHERE id = ? AND x = ?"
        out = _adapt_sql(sql, "postgresql")
        self.assertIn("%s", out)
        self.assertNotIn("?", out)

    def test_scalar_dict_row(self):
        self.assertEqual(_scalar({"c": 5}), 5)


class DatabasePostgresMockTests(unittest.TestCase):
    def test_undo_last_postgres_mock(self):
        mock_conn = mock.MagicMock()
        mock_cur = mock.MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_conn.closed = False
        mock_cur.fetchone.side_effect = [{"count": 3}, None, None]

        with mock.patch("database.psycopg2") as mock_pg:
            mock_pg.connect.return_value = mock_conn
            with mock.patch("database.db_config.get_database_url", return_value="postgresql://x"):
                with mock.patch.object(Database, "_bootstrap_postgres"):
                    db = Database()
                    db.undo_last()
                    self.assertTrue(mock_cur.execute.called)


if __name__ == "__main__":
    unittest.main()
