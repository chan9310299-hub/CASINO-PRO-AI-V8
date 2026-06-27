import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

APP_DIR = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP_DIR))

from ai.top_reasons import build_top_analysis_reasons
from ui_ko import EXP_DETAIL, EXP_LEARNING, HOME_LAYOUT_ORDER
from v10_stats import build_v10_home_stats
from v10_ui import render_v10_prediction_card
from roadmap_ai import RoadmapAI
from database import Database
from test_ai import _build_inputs


class V10LayoutTests(unittest.TestCase):
    def setUp(self):
        self.app_source = (APP_DIR / "app.py").read_text(encoding="utf-8")

    def test_home_layout_order(self):
        self.assertEqual(
            HOME_LAYOUT_ORDER,
            (
                "recent_history",
                "input_buttons",
                "ai_prediction",
                "big_road",
                "six_grid",
                "performance_summary",
            ),
        )

    def test_big_road_before_six_grid_in_source(self):
        main = self.app_source.split("# --- App ---")[1]
        big_idx = main.find("render_bigroad(bigroad)")
        six_idx = main.find("render_six_grid(history)")
        self.assertLess(big_idx, six_idx)

    def test_no_voter_summary_on_home(self):
        main = self.app_source.split("# --- App ---")[1]
        home_end = main.find("with st.expander(EXP_DETAIL")
        home_block = main[:home_end]
        self.assertNotIn("AI 판단 요약", home_block)
        self.assertNotIn("Voter Summary", home_block)

    def test_expanders_present(self):
        for name in ("EXP_DETAIL", "EXP_PERF", "EXP_LEARNING", "EXP_BACKUP", "EXP_ADVANCED"):
            self.assertIn(name, self.app_source)

    def test_sticky_prediction(self):
        self.assertIn("sticky_prediction_open", self.app_source)
        self.assertIn("render_v10_prediction_card", self.app_source)

    def test_v10_home_stats_fields(self):
        self.assertIn("오늘 적중률", (APP_DIR / "v10_ui.py").read_text(encoding="utf-8"))
        self.assertIn("누적 적중", (APP_DIR / "v10_ui.py").read_text(encoding="utf-8"))


class V10PredictionCardTests(unittest.TestCase):
    def test_prediction_card_korean(self):
        html_out = render_v10_prediction_card(
            "P", 0.85,
            {
                "probability_p": 0.85,
                "probability_b": 0.15,
                "expected_hit_rate": 85.0,
                "risk_level": "LOW",
                "low_confidence": False,
            },
        )
        self.assertIn("플레이어", html_out)
        self.assertIn("예상 적중률", html_out)
        self.assertIn("신뢰도", html_out)
        self.assertIn("anim-bar", html_out)
        self.assertNotIn("PLAYER", html_out)

    def test_top_reasons_five(self):
        reasons = build_top_analysis_reasons(
            {
                "prediction": "P",
                "signal_breakdown": {
                    "recent_20": {"weighted_p": 2, "weighted_b": 1},
                    "bigroad": {"weighted_p": 3, "weighted_b": 1},
                    "pattern_memory": {"weighted_p": 1, "weighted_b": 0},
                },
                "risk_level": "LOW",
            },
            5,
        )
        self.assertEqual(len(reasons), 5)
        labels = {r["label"] for r in reasons}
        self.assertIn("최근 흐름", labels)


class V10NoPassTests(unittest.TestCase):
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

    def tearDown(self):
        self.db.close()
        for p in self._patches:
            p.stop()
        self._tmpdir.cleanup()

    def test_never_pass(self):
        history = ["P", "B"] * 5
        kwargs = _build_inputs(history)
        r = RoadmapAI(db=self.db).analyze(**kwargs, db=self.db)
        self.assertIn(r["prediction"], ("P", "B"))


class V10StatsTests(unittest.TestCase):
    def test_build_home_stats_keys(self):
        stats = build_v10_home_stats(
            None,
            {"recent_30_accuracy": 55, "recent_100_accuracy": 52, "total_predictions": 10, "correct": 6},
            {"current_win": 1, "current_lose": 0, "max_win": 3, "max_lose": 2},
        )
        self.assertIn("today_accuracy", stats)
        self.assertIn("total_hits", stats)


if __name__ == "__main__":
    unittest.main()
