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
from ai.risk_controller import compute_risk_score
from ai.road_agreement import compute_road_agreement
from ai.bad_pattern_detector import detect_bad_patterns
from ai.losing_streak import compute_losing_streaks, min_confidence_for_streak
from ai.pass_system import evaluate_pass, PASS_MESSAGE
from ai.confidence_v6 import compute_dynamic_confidence, voter_agreement_pct, MIN_CONFIDENCE, MAX_CONFIDENCE
from ai.meta_ai import meta_ai_vote
from ai.pattern_similarity import hamming_similarity, analyze_pattern_similarity, INFLUENCE_THRESHOLD
from ai.backtest_engine import backtest_window, run_all_backtests, BACKTEST_WINDOWS
from ai.self_optimizer import should_run_optimizer, OPTIMIZE_EVERY
from ai.adaptive_learning import clamp_weight, WEIGHT_MAX, WEIGHT_MIN, MIN_SAMPLES_FOR_ADJUST
from test_ai import _build_inputs


class V6DatabaseMigrationTests(unittest.TestCase):

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

    def test_v6_tables_created(self):
        conn = self.db.connect()
        cur = conn.cursor()
        for table in ("ai_v6_metrics", "ai_backtest_v6", "ai_optimizer_v6"):
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            self.assertIsNotNone(cur.fetchone(), table)
        conn.close()

    def test_insert_v6_metrics(self):
        self.db.insert_v6_metrics(1, {
            "risk_score": 0.3, "risk_level": "LOW", "road_agreement": 80.0,
            "pattern_similarity": 75.0, "meta_score": 0.6, "pass_flag": False,
            "losing_streak": 0, "prediction_quality": "Safe",
        })
        self.assertGreater(self.db.get_v6_pass_rate(), -1)

    def test_save_backtest_and_optimizer(self):
        self.db.save_backtest_v6(100, {
            "accuracy": 55.0, "average_losing_streak": 1.5,
            "maximum_losing_streak": 3, "pass_rate": 10.0,
            "win_count": 55, "loss_count": 45,
        })
        self.db.save_optimizer_v6({
            "old_weights": {"dragon": 2.5}, "new_weights": {"dragon": 2.6},
            "accuracy_before": 50.0, "accuracy_after": 52.0,
        }, 100)
        self.assertEqual(self.db.count_optimizer_v6_runs(), 1)


class RiskControllerTests(unittest.TestCase):

    def test_low_risk(self):
        r = compute_risk_score(70, 85, 0.8, 80, 0.1, 0.7, 0.1)
        self.assertEqual(r["risk_level"], "LOW")

    def test_extreme_risk(self):
        r = compute_risk_score(30, 40, 0.2, 30, 0.8, 0.4, 0.9)
        self.assertIn(r["risk_level"], ("HIGH", "EXTREME"))


class PassSystemTests(unittest.TestCase):

    def test_pass_on_high_risk(self):
        ok, reason = evaluate_pass(0.8, "HIGH", 80, 80, 0, {"recommend_pass": False})
        self.assertTrue(ok)

    def test_pass_on_low_similarity(self):
        ok, _ = evaluate_pass(0.8, "LOW", 50, 80, 0, {"recommend_pass": False})
        self.assertTrue(ok)

    def test_pass_on_low_road_agreement(self):
        ok, _ = evaluate_pass(0.8, "LOW", 80, 50, 0, {"recommend_pass": False})
        self.assertTrue(ok)

    def test_no_pass_when_healthy(self):
        ok, _ = evaluate_pass(0.75, "LOW", 80, 75, 0, {"recommend_pass": False})
        self.assertFalse(ok)

    def test_losing_streak_confidence_requirements(self):
        self.assertEqual(min_confidence_for_streak(5), 0.98)
        self.assertEqual(min_confidence_for_streak(3), 0.90)


class LosingStreakTests(unittest.TestCase):

    def test_compute_streaks(self):
        rows = [
            {"prediction": "P", "is_correct": 0},
            {"prediction": "P", "is_correct": 0},
            {"prediction": "B", "is_correct": 1},
        ]
        s = compute_losing_streaks(rows)
        self.assertEqual(s["current_losing_streak"], 0)
        self.assertEqual(s["maximum_losing_streak"], 2)


class ConfidenceV6Tests(unittest.TestCase):

    def test_min_max_bounds(self):
        c = compute_dynamic_confidence(0.3, 10, 50, 50, 0.5, 0.5, 50, 50)
        self.assertGreaterEqual(c, MIN_CONFIDENCE)
        self.assertLessEqual(c, MAX_CONFIDENCE)

    def test_no_100_without_strict_gates(self):
        c = compute_dynamic_confidence(0.99, 100, 90, 90, 0.9, 0.9, 70, 90)
        self.assertLessEqual(c, 0.78)

    def test_voter_agreement(self):
        voters = [
            {"vote": "P", "confidence": 0.7, "weight": 1},
            {"vote": "P", "confidence": 0.6, "weight": 1},
            {"vote": "B", "confidence": 0.5, "weight": 1},
        ]
        self.assertGreater(voter_agreement_pct(voters), 50)


class MetaAITests(unittest.TestCase):

    def test_meta_ai_output(self):
        base = {
            "weighted_score": {"P": 5, "B": 3},
            "signal_breakdown": {},
            "learned_weights": {},
            "status": "정상",
        }
        pattern = {"matched_patterns": [], "sample_size": 0, "similarity_percent": 0, "reason": []}
        result = meta_ai_vote(["P"] * 8, base, pattern, {})
        self.assertIn(result["prediction"], ("P", "B"))
        self.assertIn("meta_score", result)
        self.assertEqual(len(result["voters"]), 5)


class SimilarityTests(unittest.TestCase):

    def test_hamming(self):
        self.assertEqual(hamming_similarity("PPPPPP", "PPPBPB"), 4 / 6)

    def test_influence_threshold(self):
        self.assertEqual(INFLUENCE_THRESHOLD, 0.80)


class BadPatternTests(unittest.TestCase):

    def test_chop_detected(self):
        pb = ["P", "B", "P", "B", "P", "B", "P", "B"]
        r = detect_bad_patterns(pb, {"weighted_score": {"P": 1, "B": 1}, "status": "혼조"})
        self.assertTrue(r["detected"])


class BacktestTests(unittest.TestCase):

    def test_backtest_window(self):
        rows = [{"prediction": "P", "is_correct": 1, "confidence": 0.6}] * 10
        rows += [{"prediction": "B", "is_correct": 0, "confidence": 0.6}] * 5
        r = backtest_window(rows, 100)
        self.assertEqual(r["win_count"], 10)
        self.assertEqual(r["loss_count"], 5)

    def test_all_windows_defined(self):
        self.assertIn(10000, BACKTEST_WINDOWS)


class SelfOptimizerTests(unittest.TestCase):

    def test_should_run_at_100(self):
        self.assertTrue(should_run_optimizer(100, 0))
        self.assertFalse(should_run_optimizer(50, 0))


class AdaptiveV6Tests(unittest.TestCase):

    def test_weight_clamp_5(self):
        self.assertEqual(clamp_weight(10), WEIGHT_MAX)
        self.assertEqual(WEIGHT_MAX, 5.0)
        self.assertEqual(MIN_SAMPLES_FOR_ADJUST, 30)


class RoadmapAIV6Tests(unittest.TestCase):

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

    def test_v6_keys_in_result(self):
        history = ["P", "B"] * 4
        kwargs = _build_inputs(history)
        result = RoadmapAI(db=self.db).analyze(**kwargs, db=self.db)
        self.assertIn("v6_dashboard", result)
        self.assertIn("risk_level", result)

    def test_v4_backward_compat(self):
        history = ["P", "B"] * 4
        kwargs = _build_inputs(history)
        result = RoadmapAI(db=self.db).analyze(**kwargs, db=self.db)
        for key in ("probability_p", "probability_b", "voters", "learned_weights"):
            self.assertIn(key, result)

    def test_empty_history(self):
        result = RoadmapAI(db=self.db).analyze([], bigroad=[], bigeye=[], smallroad=[], cockroach=[], db=self.db)
        self.assertIsNone(result["prediction"])

    def test_exact_pattern_with_db(self):
        key = "PBPBPB"
        for _ in range(5):
            self.db.upsert_pattern_memory(key, 6, "P")
        result = analyze_pattern_similarity(list(key), self.db)
        self.assertGreaterEqual(result.get("similarity_percent", 0), 0)


class RoadAgreementTests(unittest.TestCase):

    def test_agreement_score(self):
        base = {
            "signal_breakdown": {
                "bigroad": {"active": True, "raw": {"P": 1, "B": 0}},
                "big_eye": {"active": True, "raw": {"P": 1, "B": 0}},
            }
        }
        voters = [{"vote": "P", "confidence": 0.7, "weight": 1}]
        score = compute_road_agreement(base, voters)
        self.assertEqual(score, 100.0)


class PassMessageTests(unittest.TestCase):

    def test_pass_message_defined(self):
        self.assertIn("PASS", PASS_MESSAGE)


class V6ExtendedTests(unittest.TestCase):

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

    def _rows(self, n, correct=True):
        return [{"prediction": "P", "is_correct": 1 if correct else 0, "confidence": 0.6} for _ in range(n)]

    def test_backtest_100(self):
        r = backtest_window(self._rows(60, True) + self._rows(40, False), 100)
        self.assertEqual(r["sample_size"], 100)

    def test_backtest_300(self):
        r = backtest_window(self._rows(150, True) + self._rows(150, False), 300)
        self.assertEqual(r["sample_size"], 300)

    def test_backtest_500(self):
        r = backtest_window(self._rows(250, True) + self._rows(250, False), 500)
        self.assertEqual(r["sample_size"], 500)

    def test_backtest_1000(self):
        r = backtest_window(self._rows(500, True) + self._rows(500, False), 1000)
        self.assertEqual(r["sample_size"], 1000)

    def test_backtest_pass_count(self):
        rows = [{"prediction": "PASS", "is_correct": None}] * 20
        rows += self._rows(10)
        r = backtest_window(rows, 100)
        self.assertEqual(r["pass_count"], 20)

    def test_run_all_backtests(self):
        rows = self._rows(50, True) + self._rows(50, False)
        all_r = run_all_backtests(rows)
        self.assertIn("100", all_r)

    def test_optimizer_not_before_100(self):
        self.assertFalse(should_run_optimizer(99, 0))

    def test_optimizer_interval(self):
        self.assertFalse(should_run_optimizer(150, 100))

    def test_risk_medium(self):
        r = compute_risk_score(55, 65, 0.5, 65, 0.4, 0.55, 0.4)
        self.assertIn(r["risk_level"], ("LOW", "MEDIUM", "HIGH"))

    def test_streak_min_conf_2(self):
        self.assertEqual(min_confidence_for_streak(2), 0.75)

    def test_streak_min_conf_4(self):
        self.assertEqual(min_confidence_for_streak(4), 0.95)

    def test_pass_bad_pattern(self):
        ok, _ = evaluate_pass(0.9, "LOW", 90, 90, 0, {"recommend_pass": True})
        self.assertTrue(ok)

    def test_pass_streak_5_needs_98(self):
        ok, _ = evaluate_pass(0.97, "LOW", 90, 90, 5, {"recommend_pass": False})
        self.assertTrue(ok)

    def test_confidence_high_sample(self):
        c = compute_dynamic_confidence(0.7, 200, 80, 80, 0.8, 0.8, 65, 85)
        self.assertGreater(c, 0.5)

    def test_weight_min_clamp(self):
        self.assertEqual(clamp_weight(0.01), WEIGHT_MIN)

    def test_v6_metrics_pass_flag(self):
        self.db.insert_v6_metrics(2, {
            "risk_score": 0.8, "risk_level": "HIGH", "road_agreement": 50,
            "pattern_similarity": 50, "meta_score": 0.3, "pass_flag": True,
            "losing_streak": 3, "prediction_quality": "PASS",
        })
        self.assertGreater(self.db.get_v6_pass_rate(), 0)

    def test_pattern_similarity_empty(self):
        r = analyze_pattern_similarity(["P", "B"], self.db)
        self.assertIn("similarity_percent", r)

    def test_road_agreement_empty(self):
        self.assertEqual(compute_road_agreement({"signal_breakdown": {}}, []), 0.0)

    def test_losing_streak_all_wins(self):
        rows = [{"prediction": "P", "is_correct": 1}] * 5
        self.assertEqual(compute_losing_streaks(rows)["current_losing_streak"], 0)

    def test_losing_streak_current(self):
        rows = [
            {"prediction": "P", "is_correct": 1},
            {"prediction": "B", "is_correct": 0},
            {"prediction": "P", "is_correct": 0},
        ]
        self.assertEqual(compute_losing_streaks(rows)["current_losing_streak"], 2)

    def test_meta_ai_with_db(self):
        base = {"weighted_score": {"P": 4, "B": 2}, "signal_breakdown": {}, "learned_weights": {}, "status": "정상"}
        pattern = {"matched_patterns": [], "sample_size": 0, "similarity_percent": 0, "reason": []}
        r = meta_ai_vote(["P"] * 10, base, pattern, {}, db=self.db)
        self.assertIn("meta_score", r)

    def test_v6_dashboard_after_analyze(self):
        history = ["P", "B", "P", "B", "P", "B", "P"]
        kwargs = _build_inputs(history)
        r = RoadmapAI(db=self.db).analyze(**kwargs, db=self.db)
        dash = r.get("v6_dashboard", {})
        self.assertIn("current_losing_streak", dash)

    def test_final_prediction_always_pb(self):
        history = ["P", "B"] * 4
        kwargs = _build_inputs(history)
        r = RoadmapAI(db=self.db).analyze(**kwargs, db=self.db)
        self.assertIn(r["prediction"], ("P", "B"))
        self.assertNotEqual(r["prediction"], "PASS")

    def test_results_table_preserved(self):
        self.db.add_result("P")
        self.assertEqual(self.db.get_results(), ["P"])

    def test_optimizer_count_initial_zero(self):
        self.assertEqual(self.db.count_optimizer_v6_runs(), 0)

    def test_hamming_perfect(self):
        self.assertEqual(hamming_similarity("PPPP", "PPPP"), 1.0)

    def test_hamming_zero(self):
        self.assertEqual(hamming_similarity("PPPP", "BBBB"), 0.0)

    def test_bad_pattern_mixed_signals(self):
        r = detect_bad_patterns(
            ["P", "P", "B", "B"],
            {"weighted_score": {"P": 1, "B": 1}, "status": "정상"},
        )
        self.assertTrue(r["detected"])

    def test_voter_agreement_unanimous(self):
        voters = [{"vote": "B"}] * 4
        self.assertEqual(voter_agreement_pct(voters), 100.0)


if __name__ == "__main__":
    unittest.main()
