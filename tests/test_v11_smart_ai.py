import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

APP_DIR = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP_DIR))

from ai.final_prediction import assert_final_prediction, compute_expected_hit_rate
from ai.protection_mode import apply_protection_mode
from ai.similar_pattern_summary import build_similar_pattern_summary
from ai.top_reasons import ANALYSIS_BUCKETS, build_top_analysis_reasons
from ai.v11_confidence import (
    PROTECTION_WARNING,
    apply_protection_confidence_penalty,
    compute_smart_expected_hit_rate,
    confidence_label,
)
from roadmap_ai import RoadmapAI
from database import Database
from test_ai import _build_inputs
from ui_ko import confidence_label_ko
from v10_ui import render_v10_prediction_card


class V11ConfidenceTests(unittest.TestCase):
    def test_confidence_four_levels(self):
        self.assertEqual(confidence_label(0.90), "Very High")
        self.assertEqual(confidence_label(0.75), "High")
        self.assertEqual(confidence_label(0.55), "Medium")
        self.assertEqual(confidence_label(0.40), "Low")

    def test_confidence_korean_four_levels(self):
        self.assertEqual(confidence_label_ko(0.90), "매우 높음")
        self.assertEqual(confidence_label_ko(0.75), "높음")
        self.assertEqual(confidence_label_ko(0.55), "보통")
        self.assertEqual(confidence_label_ko(0.40), "낮음")

    def test_smart_expected_hit_rate_exists(self):
        hit = compute_smart_expected_hit_rate(
            0.72, 0.72, 0.28, "P",
            recent_accuracy_pct=65.0,
            signal_agreement=0.8,
            pattern_memory_strength=70.0,
            road_consensus=75.0,
            risk_level="LOW",
            sample_size=20,
        )
        self.assertGreater(hit, 50)
        self.assertLessEqual(hit, 99.0)

    def test_weak_data_caps_hit_rate(self):
        hit = compute_smart_expected_hit_rate(
            0.80, 0.80, 0.20, "P",
            sample_size=5,
            low_confidence=True,
        )
        self.assertLessEqual(hit, 60.0)

    def test_compute_expected_hit_rate_accepts_v11_kwargs(self):
        hit = compute_expected_hit_rate(
            0.72, 0.72, 0.28, "P",
            recent_accuracy_pct=60.0,
            signal_agreement=0.7,
            sample_size=12,
        )
        self.assertIsInstance(hit, float)


class V11SimilarPatternTests(unittest.TestCase):
    def test_similar_pattern_summary_korean(self):
        summary = build_similar_pattern_summary({
            "matched_patterns": [{"pattern_key": "PPBB", "total": 12}],
            "sample_size": 12,
            "p_probability": 0.65,
            "b_probability": 0.35,
            "similarity_percent": 80.0,
        }, "P")
        self.assertGreater(summary["similar_count"], 0)
        self.assertIn("플레이어", summary["favor"])
        self.assertNotIn("pattern_key", summary["summary"])

    def test_empty_similar_pattern_summary(self):
        summary = build_similar_pattern_summary({}, None)
        self.assertEqual(summary["similar_count"], 0)
        self.assertIn("없음", summary["summary"])


class V11ProtectionTests(unittest.TestCase):
    def test_protection_lowers_confidence_not_block(self):
        blocked, _, meta = apply_protection_mode(
            0.85, "HIGH", 70.0, 4, enabled=True,
        )
        self.assertFalse(blocked)
        self.assertTrue(meta["prediction_allowed"])
        lowered = apply_protection_confidence_penalty(0.85, meta, True)
        self.assertLess(lowered, 0.85)

    def test_protection_warning_constant(self):
        self.assertIn("위험", PROTECTION_WARNING)
        self.assertIn("신뢰도", PROTECTION_WARNING)


class V11ReasonTests(unittest.TestCase):
    def test_top_five_korean_buckets(self):
        self.assertEqual(
            list(ANALYSIS_BUCKETS.keys()),
            ["최근 흐름", "로드 분석", "유사 패턴", "학습 가중치", "위험도"],
        )

    def test_top_reasons_count(self):
        reasons = build_top_analysis_reasons({
            "prediction": "P",
            "signal_breakdown": {
                "recent_10": {"weighted_p": 2, "weighted_b": 1},
                "bigroad": {"weighted_p": 3, "weighted_b": 1},
            },
            "risk_level": "LOW",
            "meta_score": 0.7,
            "voters": [{"vote": "P", "weight": 1.0, "confidence": 0.8}],
        }, 5)
        self.assertEqual(len(reasons), 5)
        labels = {r["label"] for r in reasons}
        self.assertIn("최근 흐름", labels)
        self.assertIn("위험도", labels)


class V11NoPassTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "test.db")
        self._patches = [
            mock.patch("config.DB_PATH", Path(self.db_path)),
            mock.patch("database.DB_PATH", Path(self.db_path)),
        ]
        for p in self._patches:
            p.start()
        self.db = Database()
        self.ai = RoadmapAI()

    def tearDown(self):
        self.db.close()
        for p in self._patches:
            p.stop()
        self._tmpdir.cleanup()

    def test_never_pass_final(self):
        for seq in (["P"] * 6, ["P", "B"] * 5, ["B"] * 8):
            kwargs = _build_inputs(seq)
            result = RoadmapAI(db=self.db).analyze(**kwargs, db=self.db)
            self.assertIn(result["prediction"], ("P", "B"))
            assert_final_prediction(result["prediction"])

    def test_empty_db_still_predicts(self):
        kwargs = _build_inputs([])
        result = RoadmapAI(db=self.db).analyze(**kwargs, db=self.db)
        self.assertIn(result.get("prediction"), (None, "P", "B"))


class V11LayoutTests(unittest.TestCase):
    def setUp(self):
        self.app_source = (APP_DIR / "app.py").read_text(encoding="utf-8")

    def test_prediction_after_input_buttons(self):
        main = self.app_source.split("# --- App ---")[1]
        btn_idx = main.find("render_input_buttons")
        pred_idx = main.find("render_v10_prediction_card")
        self.assertGreater(btn_idx, 0)
        self.assertGreater(pred_idx, btn_idx)

    def test_prediction_card_has_expected_hit_rate(self):
        html = render_v10_prediction_card("P", 0.75, {
            "probability_p": 0.75,
            "probability_b": 0.25,
            "expected_hit_rate": 78.5,
            "risk_level": "LOW",
            "confidence_label": "High",
            "signal_breakdown": {"recent_10": {"weighted_p": 2, "weighted_b": 1}},
            "meta_score": 0.7,
            "voters": [{"vote": "P", "weight": 1, "confidence": 0.8}],
        })
        self.assertIn("예상 적중률", html)
        self.assertIn("분석 근거", html)
        self.assertIn("최근 흐름", html)

    def test_footer_safety_text(self):
        self.assertIn("수익이나 결과를 보장하지 않습니다", self.app_source)


if __name__ == "__main__":
    unittest.main()
