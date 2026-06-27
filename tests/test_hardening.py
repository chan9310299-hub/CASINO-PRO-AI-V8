import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

APP_DIR = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP_DIR))

from database import Database
from roadmap_ai import RoadmapAI
from db_migration import MIGRATION_VERSION, get_current_version, run_migrations, verify_tables
from backup_manager import backup_database, daily_backup_if_needed, list_backups, restore_backup
from export_import import export_db_copy, export_history_csv, export_predictions_csv, import_db_safe
from mobile_ui import MOBILE_CSS, perf_v7_color, render_perf_v7_html
from ai.quality_grade import (
    INSUFFICIENT_MSG,
    calibrate_confidence,
    cold_start_mode,
    detect_unstable_pattern,
    grade_prediction,
    safe_ai_result,
    smooth_probabilities,
)
from ai.protection_mode import apply_protection_mode, PASS_MSG
from ai.pattern_ranking import rank_patterns, has_enough_pattern_data
from ai.performance_dashboard import build_performance_dashboard, health_color
from ai.backtest_report import run_backtest_report, best_worst_signals, UI_BACKTEST_WINDOWS
from ai.pass_system import evaluate_pass
from test_ai import _build_inputs


class HardeningTestBase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "test.db")
        self.backup_dir = Path(self._tmpdir.name) / "backups"
        self.export_dir = Path(self._tmpdir.name) / "exports"
        self._patches = [
            mock.patch("config.DB_PATH", Path(self.db_path)),
            mock.patch("database.DB_PATH", Path(self.db_path)),
            mock.patch("config.BACKUP_DIR", self.backup_dir),
            mock.patch("backup_manager.DB_PATH", Path(self.db_path)),
            mock.patch("backup_manager.BACKUP_DIR", self.backup_dir),
            mock.patch("export_import.DB_PATH", Path(self.db_path)),
            mock.patch("config.EXPORT_DIR", self.export_dir),
            mock.patch("export_import.EXPORT_DIR", self.export_dir),
        ]
        for p in self._patches:
            p.start()
        self.db = Database()

    def tearDown(self):
        self.db.close()
        for p in self._patches:
            p.stop()
        self._tmpdir.cleanup()


class MigrationTests(HardeningTestBase):
    def test_migration_version_stored(self):
        self.assertGreaterEqual(get_current_version(self.db.conn), 1)

    def test_all_required_tables_exist(self):
        tables = verify_tables(self.db.conn)
        for name in (
            "results", "ai_prediction_history", "ai_signal_weights",
            "ai_pattern_memory", "ai_learning_history", "ai_weight_history",
            "ai_backtest_results", "pattern_rank_cache", "schema_migrations",
        ):
            self.assertTrue(tables.get(name), name)

    def test_migration_idempotent(self):
        result = run_migrations(self.db.conn)
        self.assertFalse(result.get("migrated", True))

    def test_db_status(self):
        status = self.db.get_db_status()
        self.assertIn("version", status)
        self.assertIn("last_backup", status)
        self.assertEqual(status["target_version"], MIGRATION_VERSION)


class BackupRestoreTests(HardeningTestBase):
    def test_backup_creates_file(self):
        self.db.add_result("P")
        path = backup_database("test")
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())

    def test_list_backups(self):
        self.db.add_result("B")
        backup_database("a")
        backup_database("b")
        self.assertGreaterEqual(len(list_backups()), 2)

    def test_restore_backup(self):
        self.db.add_result("P")
        path = backup_database("restore_test")
        self.db.add_result("B")
        self.assertEqual(len(self.db.get_results()), 2)
        self.db.close()
        restore_backup(path)
        self.db = Database()
        self.assertEqual(self.db.get_results(), ["P"])

    def test_daily_backup_once(self):
        self.db.add_result("P")
        first = daily_backup_if_needed()
        second = daily_backup_if_needed()
        self.assertIsNotNone(first)
        self.assertIsNone(second)


class ExportImportTests(HardeningTestBase):
    def test_export_db(self):
        self.db.add_result("P")
        path = export_db_copy()
        self.assertTrue(path.exists())
        self.assertGreater(path.stat().st_size, 0)

    def test_export_history_csv(self):
        self.db.add_result("P")
        self.db.add_result("B")
        path = export_history_csv(self.db)
        text = path.read_text(encoding="utf-8")
        self.assertIn("P", text)
        self.assertIn("B", text)

    def test_export_predictions_csv(self):
        self.db.insert_prediction_history(
            1, "P", "P", 0.7, {"P": 1, "B": 0}, {}, ["test"]
        )
        path = export_predictions_csv(self.db)
        self.assertTrue(path.exists())

    def test_import_db_safe(self):
        self.db.add_result("P")
        exported = export_db_copy()
        self.db.add_result("B")
        self.db.close()
        result = import_db_safe(exported, backup_database)
        self.assertTrue(result["ok"])
        self.db = Database()
        self.assertEqual(self.db.get_results(), ["P"])


class QualityGradeTests(unittest.TestCase):
    def test_smooth_probabilities(self):
        p = smooth_probabilities(0.8, 0.2)
        self.assertAlmostEqual(p["P"] + p["B"], 1.0, places=3)

    def test_smooth_zero_total(self):
        p = smooth_probabilities(0, 0)
        self.assertEqual(p["P"], 0.5)

    def test_cold_start(self):
        self.assertTrue(cold_start_mode(6, 0))
        self.assertFalse(cold_start_mode(20, 20))

    def test_grade_pass_on_high_risk(self):
        self.assertEqual(grade_prediction(0.9, "HIGH", 80, False), "PASS")

    def test_grade_a(self):
        self.assertEqual(grade_prediction(0.85, "LOW", 80, False), "A")

    def test_safe_ai_result(self):
        r = safe_ai_result()
        self.assertIsNone(r["prediction"])
        self.assertIn(INSUFFICIENT_MSG, r["reason"][0])

    def test_calibrate_confidence(self):
        c = calibrate_confidence(0.8, 50, 60)
        self.assertGreater(c, 0)
        self.assertLessEqual(c, 0.99)

    def test_unstable_pattern(self):
        self.assertTrue(detect_unstable_pattern(5, 0.5, 0.1))
        self.assertFalse(detect_unstable_pattern(20, 0.8, 0.1))


class ProtectionModeTests(unittest.TestCase):
    def test_disabled(self):
        blocked, _, meta = apply_protection_mode(0.5, "LOW", 80, 5, enabled=False)
        self.assertFalse(blocked)
        self.assertTrue(meta["prediction_allowed"])

    def test_high_risk_blocks(self):
        blocked, _, meta = apply_protection_mode(0.9, "HIGH", 80, 0)
        self.assertTrue(blocked)
        self.assertFalse(meta["prediction_allowed"])

    def test_streak_requires_high_confidence(self):
        blocked, min_c, _ = apply_protection_mode(0.9, "LOW", 80, 4)
        self.assertTrue(blocked)
        self.assertGreaterEqual(min_c, 0.98)

    def test_pass_msg_constant(self):
        self.assertIn("보호", PASS_MSG)


class AIFailSafeTests(HardeningTestBase):
    def test_empty_history(self):
        r = RoadmapAI(db=self.db).analyze([], bigroad=[])
        self.assertIsNone(r["prediction"])

    def test_only_ties(self):
        history = ["T"] * 8
        r = RoadmapAI(db=self.db).analyze(history, bigroad=[])
        self.assertIsNone(r["prediction"])

    def test_short_history_under_six(self):
        history = ["P", "B", "P", "B", "P"]
        r = RoadmapAI(db=self.db).analyze(history, bigroad=[])
        self.assertIsNone(r["prediction"])

    def test_corrupted_weights_graceful(self):
        ai = RoadmapAI(weights={"bad": "x"}, db=self.db)
        kwargs = _build_inputs(["P", "B", "P", "B", "P", "B", "P"])
        r = ai.analyze(**kwargs, db=self.db, protection_mode_enabled=False)
        self.assertIn("prediction", r)

    def test_analyze_exception_returns_safe(self):
        ai = RoadmapAI(db=self.db)
        with mock.patch.object(ai._engine, "analyze", side_effect=RuntimeError("boom")):
            r = ai.analyze(["P"] * 10, bigroad=[])
        self.assertIn("reason", r)

    def test_cold_start_passes(self):
        kwargs = _build_inputs(["P", "B"] * 4)
        r = RoadmapAI(db=self.db).analyze(**kwargs, db=self.db)
        self.assertEqual(r.get("prediction"), "PASS")
        reasons = r.get("reason_in_korean") or r.get("reason") or []
        self.assertTrue(
            any(INSUFFICIENT_MSG in str(x) for x in reasons)
            or INSUFFICIENT_MSG in (r.get("status") or "")
        )


class PassBehaviorTests(unittest.TestCase):
    def test_pass_on_low_confidence(self):
        ok, _ = evaluate_pass(0.4, "LOW", 80, 80, 0, {"recommend_pass": False})
        self.assertTrue(ok)

    def test_no_pass_when_strong(self):
        ok, _ = evaluate_pass(0.85, "LOW", 80, 80, 0, {"recommend_pass": False})
        self.assertFalse(ok)


class PatternRankingTests(HardeningTestBase):
    def test_insufficient_data(self):
        self.assertFalse(has_enough_pattern_data(self.db))

    def test_rank_after_memory(self):
        for i in range(6):
            self.db.upsert_pattern_memory(f"PPBB{i}", 4, "P")
        self.assertTrue(has_enough_pattern_data(self.db))
        ranked = rank_patterns(self.db, 5)
        self.assertGreater(len(ranked), 0)
        self.assertIn("pattern", ranked[0])

    def test_refresh_cache(self):
        self.db.upsert_pattern_memory("PPP", 3, "P")
        self.db.refresh_pattern_rank_cache()
        rows = self.db.get_pattern_rank_top(5)
        self.assertGreaterEqual(len(rows), 1)


class PerformanceDashboardTests(HardeningTestBase):
    def test_health_gray_insufficient(self):
        self.assertEqual(health_color(5, 50, "LOW"), "gray")

    def test_build_dashboard(self):
        self.db.add_result("P")
        m = build_performance_dashboard(self.db, ["P"])
        self.assertEqual(m["total_input_hands"], 1)
        self.assertIn("health_color", m)


class BacktestReportTests(HardeningTestBase):
    def _seed_predictions(self, n=20):
        for i in range(n):
            pred = "P" if i % 2 == 0 else "B"
            actual = pred if i % 3 != 0 else ("B" if pred == "P" else "P")
            self.db.insert_prediction_history(
                i + 1, "P", pred, 0.65,
                {"P": 1, "B": 0},
                {"dragon": {"vote": pred, "weight": 2.0}},
                ["test"],
            )
            self.db.update_prediction_actual(i + 1, actual, 1 if pred == actual else 0)

    def test_backtest_windows(self):
        self._seed_predictions(30)
        report = run_backtest_report(self.db)
        for w in UI_BACKTEST_WINDOWS:
            self.assertIn(str(w), report)

    def test_best_worst_signals(self):
        rows = self.db.get_resolved_predictions_pb()
        best, worst = best_worst_signals(rows)
        self.assertIsInstance(best, str)

    def test_save_backtest_report(self):
        self.db.save_backtest_report(100, {
            "accuracy": 55.0, "average_losing_streak": 1.0,
            "maximum_losing_streak": 2, "pass_rate": 10.0,
            "sample_size": 10, "win_count": 5, "loss_count": 5,
        }, "dragon", "chop")
        reports = self.db.get_latest_backtest_reports()
        self.assertGreaterEqual(len(reports), 1)


class MobileUITests(unittest.TestCase):
    def test_mobile_css_has_media(self):
        self.assertIn("@media", MOBILE_CSS)

    def test_perf_v7_color(self):
        self.assertEqual(perf_v7_color("green"), "#22c55e")

    def test_render_perf_v7_html(self):
        html = render_perf_v7_html({"health_color": "green", "total_input_hands": 10})
        self.assertIn("성능 대시보드", html)


class DatabaseSafetyTests(HardeningTestBase):
    def test_get_results_corrupt_row(self):
        self.db.add_result("P")
        self.db.conn.execute("INSERT INTO results (result, created_at) VALUES ('X', 'now')")
        self.db.conn.commit()
        results = self.db.get_results()
        self.assertIn("T", results)

    def test_missing_signal_weights_initialized(self):
        weights = self.db.get_all_signal_weights()
        self.assertGreater(len(weights), 0)

    def test_reset_learning_creates_backup(self):
        self.db.add_result("P")
        self.db.reset_ai_learning()
        self.assertGreaterEqual(len(list_backups()), 1)


class ProtectionIntegrationTests(HardeningTestBase):
    def test_protection_on_by_default(self):
        kwargs = _build_inputs(["P", "B"] * 10)
        for i in range(5):
            self.db.insert_prediction_history(
                i, "P", "P", 0.6, {"P": 1, "B": 0}, {}, ["x"]
            )
            self.db.update_prediction_actual(i, "B", 0)

        r = RoadmapAI(db=self.db).analyze(**kwargs, db=self.db, protection_mode_enabled=True)
        self.assertIn("protection_mode", r)

    def test_protection_off_allows_meta(self):
        kwargs = _build_inputs(["P", "B"] * 15)
        for i in range(15):
            self.db.insert_prediction_history(
                i, "P", "P", 0.85, {"P": 1, "B": 0}, {}, ["x"]
            )
            self.db.update_prediction_actual(i, "P", 1)
            self.db.upsert_pattern_memory("PPBB", 4, "P")

        r = RoadmapAI(db=self.db).analyze(
            **kwargs, db=self.db, protection_mode_enabled=False,
        )
        self.assertIn(r.get("prediction"), ("P", "B", "PASS"))


if __name__ == "__main__":
    unittest.main()
