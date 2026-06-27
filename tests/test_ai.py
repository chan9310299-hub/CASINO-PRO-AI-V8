import sys
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP_DIR))

from road_engine import RoadEngine
from bigroad import BigRoadEngine
from bigeye import BigEyeRoad
from smallroad import SmallRoad
from cockroach import CockroachRoad
from roadmap_ai import RoadmapAI
from ai.prediction_engine import PredictionEngine
from ai.scoring_config import ScoringConfig, DEFAULT_SIGNAL_WEIGHTS


def _build_inputs(history):
    bigroad = BigRoadEngine()
    bigroad.load(history)
    road = bigroad.build()
    return {
        "history": history,
        "bigroad": road,
        "bigeye": BigEyeRoad(history=history).build(),
        "smallroad": SmallRoad(history=history).build(),
        "cockroach": CockroachRoad(history=history).build(),
    }


class RoadmapAITests(unittest.TestCase):

    def _analyze(self, history, weights=None):
        kwargs = _build_inputs(history)
        return RoadmapAI(weights=weights).analyze(**kwargs)

    def test_returns_none_before_six_hands(self):
        result = self._analyze(["P", "B", "P", "B", "P"])
        self.assertIsNone(result["prediction"])
        self.assertEqual(result["confidence"], 0)
        self.assertIn("status", result)

    def test_response_shape(self):
        history = ["P", "B"] * 4
        result = self._analyze(history)

        self.assertIn(result["prediction"], ("P", "B"))
        self.assertIn("confidence", result)
        self.assertIn("weighted_score", result)
        self.assertIn("signal_breakdown", result)
        self.assertIn("reason_in_korean", result)
        self.assertIn("score", result)
        self.assertIn("reason", result)
        self.assertIn("status", result)
        self.assertIn("learned_weights", result)

        self.assertEqual(result["score"], result["weighted_score"])
        self.assertEqual(result["reason"], result["reason_in_korean"])
        self.assertIn("P", result["weighted_score"])
        self.assertIn("B", result["weighted_score"])
        self.assertTrue(len(result["reason_in_korean"]) > 0)

    def test_all_configured_signals_present(self):
        result = self._analyze(["P", "B"] * 4)
        breakdown = result["signal_breakdown"]
        expected_signals = [
            "recent_10",
            "recent_20",
            "recent_30",
            "bigroad",
            "dragon",
            "chop",
            "ping_pong",
            "double_pattern",
            "big_eye",
            "small_road",
            "cockroach_road",
            "pattern_memory",
        ]
        for signal in expected_signals:
            self.assertIn(signal, breakdown)
            self.assertIn("weight", breakdown[signal])
            self.assertIn("raw", breakdown[signal])
            self.assertIn("weighted", breakdown[signal])

    def test_weighted_score_sums_active_signals(self):
        history = ["P", "B", "P", "B", "P", "B"]
        result = self._analyze(history)
        ws = result["weighted_score"]
        base = DEFAULT_SIGNAL_WEIGHTS["base_p"] + DEFAULT_SIGNAL_WEIGHTS["base_b"]
        active_weighted = sum(
            entry["weighted"]["P"] + entry["weighted"]["B"]
            for entry in result["signal_breakdown"].values()
            if entry["active"]
        )
        self.assertAlmostEqual(ws["P"] + ws["B"], base + active_weighted, places=4)

    def test_adjustable_weight_changes_score(self):
        history = ["P"] * 8
        default = self._analyze(history)
        boosted = self._analyze(history, weights={"dragon": 10.0})
        self.assertNotEqual(
            default["weighted_score"],
            boosted["weighted_score"],
        )
        self.assertEqual(boosted["signal_breakdown"]["dragon"]["weight"], 10.0)

    def test_derived_red_favors_continuation(self):
        history = ["P", "B", "P", "B", "P", "B", "P"]
        result = self._analyze(history)
        reasons = " ".join(result["reason_in_korean"])
        self.assertIn("흐름 유지", reasons)

    def test_recent_window_reasons(self):
        history = (["P"] * 15 + ["B"] * 15)[:30]
        result = self._analyze(history)
        joined = " ".join(result["reason_in_korean"])
        self.assertIn("최근 10판", joined)
        self.assertIn("최근 20판", joined)
        self.assertIn("최근 30판", joined)

    def test_dragon_signal_active(self):
        history = ["P"] * 8
        result = self._analyze(history)
        self.assertTrue(result["signal_breakdown"]["dragon"]["active"])
        self.assertTrue(
            any("드래곤" in r or "장줄" in r for r in result["reason_in_korean"])
        )

    def test_chop_or_ping_pong_active(self):
        history = ["P", "B", "P", "B", "P", "B", "P", "B"]
        result = self._analyze(history)
        breakdown = result["signal_breakdown"]
        self.assertTrue(
            breakdown["chop"]["active"] or breakdown["ping_pong"]["active"]
        )

    def test_bigroad_trend_active(self):
        history = ["B", "B", "B", "B", "B", "B"]
        result = self._analyze(history)
        self.assertTrue(result["signal_breakdown"]["bigroad"]["active"])

    def test_status_for_insufficient_data(self):
        result = self._analyze(["P", "B", "P"])
        self.assertEqual(result["status"], "6개 입력 후 7번째부터 예측 시작")
        self.assertEqual(result["signal_breakdown"], {})


class ScoringConfigTests(unittest.TestCase):

    def test_defaults_merge_with_custom(self):
        cfg = ScoringConfig(weights={"dragon": 5.0})
        self.assertEqual(cfg.get("dragon"), 5.0)
        self.assertEqual(cfg.get("chop"), DEFAULT_SIGNAL_WEIGHTS["chop"])

    def test_as_dict_returns_copy(self):
        cfg = ScoringConfig()
        exported = cfg.as_dict()
        exported["dragon"] = 999.0
        self.assertNotEqual(cfg.get("dragon"), 999.0)


class UnifiedEngineTests(unittest.TestCase):

    def test_facade_matches_engine(self):
        history = ["P", "B", "P", "B", "P", "B", "P", "B"]
        kwargs = _build_inputs(history)

        from_engine = PredictionEngine().analyze(**kwargs)
        from_facade = RoadmapAI().analyze(**kwargs)

        for key, value in from_engine.items():
            self.assertEqual(from_facade[key], value, key)
        self.assertIn("probability_p", from_facade)
        self.assertIn("voters", from_facade)


class InterblockScenarioTests(unittest.TestCase):

    def test_wgm_ten_hand_bigroad_shape(self):
        history = ["B", "P", "P", "P", "B", "B", "P", "P", "B", "T"]
        road = RoadEngine(history).build_bigroad()
        self.assertEqual(len(road), 9)
        self.assertEqual(road[-1]["ties"], 1)

    def test_derived_roads_start_after_required_columns(self):
        history = ["P", "B", "P", "B", "P"]
        self.assertEqual(len(BigEyeRoad(history=history).build()), 3)
        self.assertEqual(len(SmallRoad(history=history).build()), 2)
        self.assertEqual(len(CockroachRoad(history=history).build()), 1)


if __name__ == "__main__":
    unittest.main()
