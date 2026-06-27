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
from ai.data_stats import get_data_counts
from ai.pattern_similarity import (
    analyze_pattern_similarity,
    hamming_similarity,
    EXACT_MIN_TOTAL,
    SIMILAR_MIN_TOTAL,
)
from ai.voting_engine import calibrate_confidence, combine_votes
from ai_learning import process_new_hand
from test_ai import _build_inputs


class DataCountTests(unittest.TestCase):

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

    def test_data_count_calculation(self):
        for r in ["P", "B", "P", "B", "P", "B", "P"]:
            self.db.add_result(r)
        history = self.db.get_results()
        counts = get_data_counts(self.db, history)
        self.assertEqual(counts["total_input_hands"], 7)
        self.assertEqual(counts["accumulated_pb_hands"], 7)
        self.assertGreaterEqual(counts["signal_count"], 12)


class PatternSimilarityTests(unittest.TestCase):

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

    def test_exact_pattern_similarity_lookup(self):
        key = "PBPBPB"
        for _ in range(EXACT_MIN_TOTAL):
            self.db.upsert_pattern_memory(key, 6, "P")
        pb = list(key)
        result = analyze_pattern_similarity(pb, self.db)
        self.assertEqual(result["prediction"], "P")
        self.assertGreater(result["sample_size"], 0)
        self.assertTrue(any("동일 패턴" in r for r in result["reason"]))

    def test_similar_pattern_lookup(self):
        stored = "PBPBPB"
        query = "PBPBPP"
        for _ in range(SIMILAR_MIN_TOTAL):
            self.db.upsert_pattern_memory(stored, 6, "B")
        self.assertGreaterEqual(hamming_similarity(stored, query), 0.75)
        result = analyze_pattern_similarity(list(query), self.db)
        self.assertIsNotNone(result["prediction"])
        self.assertTrue(any("유사 패턴" in r for r in result["reason"]))

    def test_insufficient_pattern_sample(self):
        result = analyze_pattern_similarity(["P", "B", "P", "B", "P", "B"], self.db)
        self.assertIsNone(result["prediction"])
        self.assertIn("패턴 표본 부족", result["reason"][0])


class VotingEngineTests(unittest.TestCase):

    def test_confidence_cap_under_low_sample_size(self):
        capped = calibrate_confidence(0.95, sample_size=10, ai_accuracy_pct=70.0)
        self.assertLessEqual(capped, 0.62)
        self.assertGreaterEqual(capped, 0.50)

    def test_voting_engine_output_format(self):
        base = {
            "prediction": "P",
            "confidence": 0.7,
            "weighted_score": {"P": 5.0, "B": 3.0},
            "learned_weights": {"dragon": 2.5},
            "status": "정상 구간",
        }
        pattern = {
            "prediction": "P",
            "confidence": 0.6,
            "matched_patterns": [{"total": 10}],
            "sample_size": 10,
            "reason": ["동일 패턴 과거 10회 중 PLAYER 우세"],
        }
        result = combine_votes(["P"] * 8, base, pattern, {"ai_accuracy_pct": 60.0})
        self.assertIn(result["prediction"], ("P", "B"))
        self.assertIn("probability_p", result)
        self.assertIn("probability_b", result)
        self.assertEqual(len(result["voters"]), 5)
        for voter in result["voters"]:
            self.assertIn("name", voter)
            self.assertIn("vote", voter)
            self.assertIn("confidence", voter)
            self.assertIn("weight", voter)
            self.assertIn("reason", voter)


class RoadmapAIV4Tests(unittest.TestCase):

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

    def test_roadmap_ai_backward_compatibility(self):
        history = ["P", "B"] * 4
        kwargs = _build_inputs(history)
        result = RoadmapAI().analyze(**kwargs)
        for key in (
            "prediction", "confidence", "score", "weighted_score",
            "signal_breakdown", "reason", "status", "learned_weights",
            "probability_p", "probability_b", "voters",
            "pattern_similarity", "data_counts",
        ):
            self.assertIn(key, result)
        self.assertEqual(result["score"], result["weighted_score"])

    def test_v4_with_db_has_voters(self):
        history = ["P", "B"] * 4
        kwargs = _build_inputs(history)
        result = RoadmapAI(db=self.db).analyze(**kwargs, db=self.db)
        self.assertGreaterEqual(len(result["voters"]), 5)
        names = {v.get("name") for v in result["voters"]}
        self.assertIn("trend_ai", names)

    def test_empty_history_no_crash(self):
        result = RoadmapAI(db=self.db).analyze([], bigroad=[], bigeye=[], smallroad=[], cockroach=[], db=self.db)
        self.assertIsNone(result["prediction"])
        self.assertIn("data_counts", result)

    def test_ties_excluded_from_pattern_memory(self):
        for r in ["P", "T", "B", "T", "P", "B", "P", "B"]:
            process_new_hand(self.db, r, lambda h: {"prediction": None})
        cur = self.db.conn.cursor()
        cur.execute("SELECT pattern_key FROM ai_pattern_memory")
        for row in cur.fetchall():
            self.assertNotIn("T", row[0])


class UIHelperTests(unittest.TestCase):

    def test_render_data_count_card_no_crash_without_counts(self):
        import app as app_module
        try:
            app_module.render_data_count_card(None)
            app_module.render_data_count_card({})
        except Exception as exc:
            self.fail(f"render_data_count_card crashed: {exc}")

    def test_render_ai_analysis_no_crash_without_data_counts(self):
        import app as app_module
        try:
            app_module.render_ai_analysis("P", 0.6, "정상", ["테스트"], {})
        except Exception as exc:
            self.fail(f"render_ai_analysis crashed: {exc}")


if __name__ == "__main__":
    unittest.main()
