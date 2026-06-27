import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

APP_DIR = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP_DIR))

import storage as storage_module
from database import Database
from db_config import get_database_url, is_cloud_db_enabled


class DbConfigTests(unittest.TestCase):
    def test_no_database_url_by_default(self):
        with mock.patch("db_config.get_database_url", return_value=None):
            self.assertFalse(is_cloud_db_enabled())

    def test_database_url_from_env(self):
        with mock.patch("db_config.get_database_url", return_value="postgresql://u:p@localhost/db"):
            import db_config as dc
            self.assertTrue(dc.is_cloud_db_enabled())
            self.assertIn("postgresql", dc.get_database_url() or "")


class SQLiteFallbackTests(unittest.TestCase):
    def setUp(self):
        storage_module._backend_instance = None
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "test.db")
        self._patches = [
            mock.patch("config.DB_PATH", Path(self.db_path)),
            mock.patch("database.DB_PATH", Path(self.db_path)),
            mock.patch("db_config.get_database_url", return_value=None),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        if storage_module._backend_instance is not None:
            storage_module._backend_instance.close()
        storage_module._backend_instance = None
        for p in self._patches:
            p.stop()
        self._tmpdir.cleanup()

    def test_sqlite_fallback_works(self):
        backend = storage_module.get_storage_backend()
        self.assertFalse(backend.is_cloud)
        backend.save_hand("P")
        backend.save_hand("B")
        self.assertEqual(backend.load_history(), ["P", "B"])

    def test_app_does_not_crash_without_cloud(self):
        backend = storage_module.get_storage_backend()
        stats = backend.load_ai_stats()
        self.assertIn("total_predictions", stats)


class CloudAdapterTests(unittest.TestCase):
    def test_init_cloud_tables_on_mock_conn(self):
        from pg_database import init_cloud_tables

        conn = mock.MagicMock()
        cur = mock.MagicMock()
        conn.cursor.return_value = cur
        init_cloud_tables(conn)
        self.assertTrue(cur.execute.called)
        conn.commit.assert_called()

    def test_postgres_database_wrapper(self):
        from database import Database

        mock_conn = mock.MagicMock()
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"c": 0}
        mock_cursor.fetchall.return_value = []

        with mock.patch("database.psycopg2") as mock_pg:
            mock_pg.connect.return_value = mock_conn
            with mock.patch("database.db_config.get_database_url", return_value="postgresql://test"):
                with mock.patch.object(Database, "_bootstrap_postgres"):
                    db = Database()
                    db.add_result("P")
                    self.assertTrue(db.is_postgres)


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "test.db")
        self._patches = [
            mock.patch("config.DB_PATH", Path(self.db_path)),
            mock.patch("database.DB_PATH", Path(self.db_path)),
        ]
        for p in self._patches:
            p.start()
        self.sqlite = Database()
        self.sqlite.add_result("P")
        self.sqlite.add_result("B")

        self.mock_pg = mock.MagicMock()
        self.mock_pg.conn = mock.MagicMock()
        self.mock_pg.get_results = mock.MagicMock(return_value=[])
        self.mock_pg.get_all_predictions = mock.MagicMock(return_value=[])
        cur = mock.MagicMock()
        self.mock_pg.conn.cursor.return_value = cur
        cur.fetchone.side_effect = [
            {"c": 0},  # results count
            None,  # pred duplicate check
            None,  # pattern duplicate
        ]

    def tearDown(self):
        self.sqlite.close()
        for p in self._patches:
            p.stop()
        self._tmpdir.cleanup()

    def test_migration_skips_duplicates(self):
        from cloud_migration import migrate_sqlite_to_postgres

        cur = self.mock_pg.conn.cursor.return_value
        cur.fetchone.side_effect = [None]  # checksum not found
        with mock.patch("cloud_migration._migration_already_done", return_value=True):
            result = migrate_sqlite_to_postgres(self.sqlite, self.mock_pg)
        self.assertTrue(result["skipped"])

    def test_migration_runs_once(self):
        from cloud_migration import migrate_sqlite_to_postgres

        cur = self.mock_pg.conn.cursor.return_value
        cur.fetchone.side_effect = [
            {"c": 0},
            None,
        ]
        with mock.patch("cloud_migration._migration_already_done", return_value=False):
            with mock.patch("backup_manager.backup_database"):
                result = migrate_sqlite_to_postgres(self.sqlite, self.mock_pg)
        self.assertTrue(result["ok"])
        self.assertFalse(result["skipped"])


class CloudPersistenceTests(unittest.TestCase):
    def setUp(self):
        storage_module._backend_instance = None
        self.store: dict = {"history": []}
        self.mock_db = mock.MagicMock()
        self.mock_db.backend = "postgresql"
        self.mock_db.get_results.side_effect = lambda: list(self.store["history"])
        self.mock_db.add_result.side_effect = lambda r: self.store["history"].append(r)
        self.mock_db.get_learning_stats.return_value = {"total_predictions": 0, "pending": 0}
        self.mock_db.get_pattern_memory_count.return_value = 0
        self.mock_db.get_db_status.return_value = {
            "storage_mode": "cloud",
            "cloud_connected": True,
        }
        self.mock_db.get_last_save_time.return_value = "2026-01-01 12:00:00"
        self.mock_db.close = mock.MagicMock()

    def tearDown(self):
        storage_module._backend_instance = None

    def test_history_persists_through_reload_mock(self):
        with mock.patch("db_config.get_database_url", return_value="postgresql://mock"):
            with mock.patch("database.psycopg2"):
                with mock.patch.object(storage_module.Database, "__init__", lambda self, force_sqlite=False: None):
                    b1 = storage_module.StorageBackend(db=self.mock_db)
                    b1.save_hand("P")
                    b1.save_hand("B")
                    b2 = storage_module.StorageBackend(db=self.mock_db)
                    self.assertEqual(b2.load_history(), ["P", "B"])


class V12UITests(unittest.TestCase):
    def test_db_status_card_korean(self):
        from v12_ui import render_v12_db_status_card, render_cloud_storage_banner

        html = render_v12_db_status_card({
            "storage_mode": "local",
            "cloud_connected": False,
            "total_input_hands": 10,
            "total_ai_predictions": 5,
            "pattern_memory_count": 3,
            "last_save_time": "2026-01-01",
        })
        self.assertIn("저장 방식", html)
        self.assertIn("로컬 SQLite", html)
        self.assertIn("연결 안 됨", html)
        warn = render_cloud_storage_banner(False)
        self.assertIn("로컬 저장", warn)
        ok = render_cloud_storage_banner(True)
        self.assertIn("클라우드 DB 연결됨", ok)


class V12AppSourceTests(unittest.TestCase):
    def setUp(self):
        self.app_source = (APP_DIR / "app.py").read_text(encoding="utf-8")

    def test_storage_backend_used(self):
        self.assertIn("get_storage_backend", self.app_source)
        self.assertIn("render_v12_db_status_card", self.app_source)

    def test_migration_button_korean(self):
        self.assertIn("SQLite → 클라우드 DB 이전", self.app_source)


if __name__ == "__main__":
    unittest.main()
