import os
import sys
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP_DIR))

from ui_ko import (
    BTN_PLAYER,
    EXP_BACKUP,
    FORBIDDEN_MAIN_UI_ENGLISH,
    HOME_LAYOUT_ORDER,
    SIX_GRID_TITLE,
    VOTER_LABELS_KO,
    confidence_label_ko,
    prediction_label_ko,
    protection_status_ko,
    risk_level_ko,
    vote_label_ko,
)
from mobile_ui import MOBILE_CSS, mobile_pro_open
from roadmap_ai import RoadmapAI
from database import Database
from test_ai import _build_inputs


class KoreanUILabelTests(unittest.TestCase):
    def test_app_name_korean(self):
        from local_config import APP_NAME
        self.assertIn("CASINO PRO AI", APP_NAME)

    def test_prediction_labels(self):
        self.assertEqual(prediction_label_ko("P"), "플레이어")
        self.assertEqual(prediction_label_ko("B"), "뱅커")

    def test_vote_neutral_korean(self):
        self.assertEqual(vote_label_ko(None), "중립")

    def test_confidence_korean(self):
        self.assertEqual(confidence_label_ko(0.8), "높음")
        self.assertEqual(confidence_label_ko(0.6), "보통")
        self.assertEqual(confidence_label_ko(0.4), "낮음")

    def test_risk_korean(self):
        self.assertEqual(risk_level_ko("EXTREME"), "매우 높음")
        self.assertEqual(risk_level_ko("LOW"), "낮음")

    def test_protection_status_korean(self):
        self.assertEqual(protection_status_ko({"risk_level": "LOW"}, True), "예측 허용")
        self.assertEqual(protection_status_ko({"risk_level": "HIGH"}, True), "위험 구간")

    def test_voter_labels_all_korean(self):
        english_only = ("Trend AI", "Road AI", "Pattern AI", "Memory AI", "Risk AI")
        for label in VOTER_LABELS_KO.values():
            self.assertNotIn(label, english_only)

    def test_button_labels_korean(self):
        self.assertIn("플레이어", BTN_PLAYER)

    def test_layout_order_includes_six_grid(self):
        self.assertLess(
            HOME_LAYOUT_ORDER.index("ai_prediction"),
            HOME_LAYOUT_ORDER.index("big_road"),
        )
        self.assertLess(
            HOME_LAYOUT_ORDER.index("big_road"),
            HOME_LAYOUT_ORDER.index("six_grid"),
        )


class KoreanUIAppSourceTests(unittest.TestCase):
    def setUp(self):
        app_path = APP_DIR / "app.py"
        self.app_source = app_path.read_text(encoding="utf-8")

    def test_six_grid_visible_not_in_expander(self):
        idx_six = self.app_source.find("render_six_grid(history)")
        idx_exp = self.app_source.rfind('expander("🎲 6매 GRID"')
        self.assertGreater(idx_six, 0)
        self.assertEqual(idx_exp, -1)

    def test_layout_order_in_source(self):
        main = self.app_source.split("# --- App ---")[1]
        ai_idx = main.find("render_v10_prediction_card")
        big_idx = main.find("render_bigroad(bigroad)")
        six_idx = main.find("render_six_grid(history)")
        self.assertLess(ai_idx, big_idx)
        self.assertLess(big_idx, six_idx)

    def test_korean_prediction_card_markers(self):
        v10_src = (APP_DIR / "v10_ui.py").read_text(encoding="utf-8")
        self.assertIn("플레이어", v10_src)
        self.assertIn("예상 적중률", v10_src)
        self.assertIn("render_v10_prediction_card", self.app_source)

    def test_no_forbidden_english_in_v10_prediction(self):
        block = (APP_DIR / "v10_ui.py").read_text(encoding="utf-8")
        for word in FORBIDDEN_MAIN_UI_ENGLISH:
            self.assertNotIn(word, block, msg=f"Found forbidden English: {word}")

    def test_backup_expander_korean(self):
        self.assertIn("EXP_BACKUP", self.app_source)

    def test_mobile_css_sticky_and_font(self):
        self.assertIn("sticky-input-wrap", MOBILE_CSS)
        self.assertIn("60px", MOBILE_CSS)
        self.assertIn("Noto Sans KR", self.app_source)


class FinalPredictionNeverPassTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "test.db")
        from unittest import mock
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

    def test_analyze_never_pass(self):
        history = ["P", "B"] * 5
        kwargs = _build_inputs(history)
        r = RoadmapAI(db=self.db).analyze(**kwargs, db=self.db)
        self.assertIn(r["prediction"], ("P", "B"))
        self.assertNotEqual(r.get("prediction"), "PASS")


class AppImportTests(unittest.TestCase):
    def test_core_modules_import(self):
        import ui_ko  # noqa: F401
        import mobile_ui  # noqa: F401
        import roadmap_ai  # noqa: F401
        import access_guard  # noqa: F401


if __name__ == "__main__":
    unittest.main()
