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
from ai_learning import (
    calculate_learning_stats,
    compute_is_correct,
    ensure_prediction_logged,
    process_new_hand,
)


def _sample_ai_result(prediction="P"):
    return {
        "prediction": prediction,
        "confidence": 0.62,
        "weighted_score": {"P": 5.0, "B": 3.0},
        "score": {"P": 5.0, "B": 3.0},
        "signal_breakdown": {"dragon": {"active": True, "weight": 2.5}},
        "reason_in_korean": ["테스트 신호"],
        "reason": ["테스트 신호"],
        "status": "정상 구간",
    }


def _mock_analyze(history):
    pb = [x for x in history if x in ("P", "B")]
    if len(pb) < 6:
        return {
            "prediction": None,
            "confidence": 0,
            "weighted_score": {"P": 0, "B": 0},
            "signal_breakdown": {},
            "reason_in_korean": ["데이터 부족"],
        }
    return _sample_ai_result("P" if pb[-1] == "B" else "B")


class AILearningDatabaseTests(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "test.db")
        self._patches = [
            mock.patch("config.DB_PATH", self.db_path),
            mock.patch("database.DB_PATH", self.db_path),
        ]
        for p in self._patches:
            p.start()
        self.db = Database()

    def tearDown(self):
        self.db.close()
        for p in self._patches:
            p.stop()
        self._tmpdir.cleanup()

    def test_table_created(self):
        conn = self.db.connect()
        cur = conn.cursor()
        cur.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='ai_prediction_history'
        """)
        self.assertIsNotNone(cur.fetchone())
        conn.close()

    def test_results_table_preserved(self):
        self.db.add_result("P")
        self.assertEqual(self.db.get_results(), ["P"])

    def test_log_prediction_insert(self):
        row_id = self.db.insert_prediction_history(
            hand_index=7,
            history_snapshot=["P", "B"] * 3,
            prediction="P",
            confidence=0.6,
            weighted_score={"P": 4.0, "B": 2.0},
            signal_breakdown_json={"dragon": {"active": True}},
            reason_json=["드래곤 추종"],
        )
        self.assertIsNotNone(row_id)
        rows = self.db.get_all_predictions()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["prediction"], "P")
        self.assertIsNone(rows[0]["actual_result"])
        self.assertIsNone(rows[0]["is_correct"])

    def test_resolve_prediction_correct(self):
        self.db.insert_prediction_history(
            hand_index=7,
            history_snapshot=["P"] * 6,
            prediction="P",
            confidence=0.6,
            weighted_score={"P": 4.0, "B": 2.0},
            signal_breakdown_json={},
            reason_json=["테스트"],
        )
        self.db.update_prediction_actual(7, "P", 1)
        rows = self.db.get_resolved_predictions_pb()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["is_correct"], 1)

    def test_resolve_prediction_wrong(self):
        self.db.insert_prediction_history(
            hand_index=7,
            history_snapshot=["P"] * 6,
            prediction="P",
            confidence=0.6,
            weighted_score={"P": 4.0, "B": 2.0},
            signal_breakdown_json={},
            reason_json=["테스트"],
        )
        self.db.update_prediction_actual(7, "B", 0)
        rows = self.db.get_resolved_predictions_pb()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["is_correct"], 0)

    def test_tie_does_not_count_in_stats(self):
        self.db.insert_prediction_history(
            hand_index=7,
            history_snapshot=["P"] * 6,
            prediction="P",
            confidence=0.6,
            weighted_score={"P": 4.0, "B": 2.0},
            signal_breakdown_json={},
            reason_json=["테스트"],
        )
        self.db.update_prediction_actual(7, "T", None)
        stats = self.db.get_learning_stats()
        self.assertEqual(stats["correct"], 0)
        self.assertEqual(stats["wrong"], 0)
        self.assertEqual(stats["total_resolved"], 0)
        self.assertEqual(stats["total_predictions"], 1)

        row = self.db.get_all_predictions()[0]
        self.assertEqual(row["actual_result"], "T")
        self.assertIsNone(row["is_correct"])

    def test_learning_stats_calculation(self):
        for i, (pred, actual, expected) in enumerate([
            ("P", "P", 1),
            ("P", "B", 0),
            ("B", "B", 1),
        ]):
            self.db.insert_prediction_history(
                hand_index=7 + i,
                history_snapshot=["P"] * 6,
                prediction=pred,
                confidence=0.6,
                weighted_score={"P": 4.0, "B": 2.0},
                signal_breakdown_json={},
                reason_json=["테스트"],
            )
            self.db.update_prediction_actual(7 + i, actual, expected)

        stats = self.db.get_learning_stats()
        self.assertEqual(stats["total_predictions"], 3)
        self.assertEqual(stats["total_resolved"], 3)
        self.assertEqual(stats["correct"], 2)
        self.assertEqual(stats["wrong"], 1)
        self.assertEqual(stats["overall_accuracy"], 66.67)
        self.assertEqual(stats["pending"], 0)

    def test_process_new_hand_flow(self):
        for r in ["P", "B", "P", "B", "P", "B"]:
            process_new_hand(self.db, r, _mock_analyze)

        pending_before = self.db.count_pending_predictions()
        self.assertEqual(pending_before, 1)

        process_new_hand(self.db, "P", _mock_analyze)
        stats = calculate_learning_stats(self.db)
        self.assertEqual(stats["total_resolved"], 1)
        self.assertEqual(stats["pending"], 1)

    def test_ensure_prediction_no_duplicate(self):
        history = ["P", "B", "P", "B", "P", "B"]
        ai = _sample_ai_result("P")
        ensure_prediction_logged(self.db, history, ai)
        ensure_prediction_logged(self.db, history, ai)
        self.assertEqual(self.db.count_all_predictions(), 1)

    def test_undo_cleans_prediction_history(self):
        for r in ["P", "B", "P", "B", "P", "B"]:
            process_new_hand(self.db, r, _mock_analyze)
        self.assertGreater(self.db.count_all_predictions(), 0)
        self.db.undo_last()
        self.assertEqual(len(self.db.get_results()), 5)

    def test_required_database_methods_exist(self):
        required = [
            "has_prediction_for_hand",
            "insert_prediction_history",
            "update_prediction_actual",
            "get_learning_stats",
            "get_unresolved_prediction",
        ]
        for name in required:
            self.assertTrue(hasattr(self.db, name), f"Missing method: {name}")

    def test_get_unresolved_prediction(self):
        self.db.insert_prediction_history(
            hand_index=7,
            history_snapshot=["P"] * 6,
            prediction="P",
            confidence=0.6,
            weighted_score={"P": 1.0, "B": 0.0},
            signal_breakdown_json={},
            reason_json=["테스트"],
        )
        unresolved = self.db.get_unresolved_prediction()
        self.assertIsNotNone(unresolved)
        self.assertEqual(unresolved["hand_index"], 7)
        self.assertIsNone(unresolved["actual_result"])

    def test_get_learning_stats_via_database(self):
        stats = self.db.get_learning_stats()
        self.assertEqual(stats["total_predictions"], 0)
        self.assertEqual(stats["pending"], 0)

    def test_empty_history_stats(self):
        stats = self.db.get_learning_stats()
        self.assertEqual(stats["total_predictions"], 0)
        self.assertEqual(stats["correct"], 0)
        self.assertEqual(stats["wrong"], 0)
        self.assertEqual(stats["overall_accuracy"], 0.0)
        self.assertEqual(stats["pending"], 0)


class ComputeIsCorrectTests(unittest.TestCase):

    def test_tie_returns_none(self):
        self.assertIsNone(compute_is_correct("P", "T"))

    def test_match(self):
        self.assertEqual(compute_is_correct("P", "P"), 1)

    def test_mismatch(self):
        self.assertEqual(compute_is_correct("P", "B"), 0)


class EmptyHistoryAppFlowTests(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "test.db")
        self._patches = [
            mock.patch("config.DB_PATH", self.db_path),
            mock.patch("database.DB_PATH", self.db_path),
        ]
        for p in self._patches:
            p.start()
        self.db = Database()

    def tearDown(self):
        self.db.close()
        for p in self._patches:
            p.stop()
        self._tmpdir.cleanup()

    def test_empty_history_does_not_crash(self):
        history = self.db.get_results()
        ai = _mock_analyze(history)
        ensure_prediction_logged(self.db, history, ai)
        stats = calculate_learning_stats(self.db)
        self.assertIsNone(ai["prediction"])
        self.assertEqual(stats["total_predictions"], 0)


if __name__ == "__main__":
    unittest.main()
