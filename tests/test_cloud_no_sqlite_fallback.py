import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

APP_DIR = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP_DIR))

from database import Database, CLOUD_DB_ERROR_MSG


class CloudSqliteFallbackTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "test.db")
        self._path_patches = [
            mock.patch("config.DB_PATH", Path(self.db_path)),
            mock.patch("database.DB_PATH", Path(self.db_path)),
        ]
        for p in self._path_patches:
            p.start()

    def tearDown(self):
        for p in self._path_patches:
            p.stop()
        self._tmpdir.cleanup()

    def test_bad_database_url_falls_back_to_sqlite(self):
        with mock.patch("database.resolve_database_url", return_value="postgresql://bad:bad@invalid/db"):
            with mock.patch("database._connect_postgresql", side_effect=Exception("connect fail")):
                db = Database()
                self.assertEqual(db.connection_error, CLOUD_DB_ERROR_MSG)
                self.assertTrue(db.cloud_fallback)
                self.assertFalse(db.is_postgres)
                self.assertIsNotNone(db.conn)
                db.record_hand("P")
                self.assertEqual(db.get_results(), ["P"])
                db.close()

    def test_bad_database_url_app_can_query_pattern_count(self):
        with mock.patch("database.resolve_database_url", return_value="postgresql://bad/db"):
            with mock.patch("database._connect_postgresql", side_effect=Exception("connect fail")):
                db = Database()
                count = db.get_pattern_memory_count()
                self.assertEqual(count, 0)
                db.close()

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
                        self.assertFalse(db.cloud_fallback)
                        db.close()


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


class PatternRankingResilienceTests(unittest.TestCase):
    def test_pattern_ranking_survives_db_error(self):
        from ai.pattern_ranking import has_enough_pattern_data, rank_patterns

        bad_db = mock.MagicMock()
        bad_db.get_pattern_memory_count.side_effect = Exception("db down")
        self.assertFalse(has_enough_pattern_data(bad_db))

        bad_db.get_pattern_memory_count.side_effect = None
        bad_db.get_pattern_memory_count.return_value = 10
        bad_db.ensure_v6_tables.side_effect = Exception("fail")
        self.assertEqual(rank_patterns(bad_db), [])

    def test_render_pattern_ranking_has_error_guard(self):
        source = (APP_DIR / "app.py").read_text(encoding="utf-8")
        idx = source.index("def render_pattern_ranking")
        block = source[idx:idx + 1400]
        self.assertIn("try:", block)
        self.assertIn("패턴 랭킹을 불러오지 못했습니다", block)
        self.assertNotIn("st.exception", block)


if __name__ == "__main__":
    unittest.main()
