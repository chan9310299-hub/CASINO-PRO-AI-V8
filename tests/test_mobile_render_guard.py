import sys
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP_DIR))


class MobileRenderGuardTests(unittest.TestCase):
    def setUp(self):
        self.app_source = (APP_DIR / "app.py").read_text(encoding="utf-8")
        self.mobile_css = (APP_DIR / "mobile_ui.py").read_text(encoding="utf-8")
        self.main_block = self.app_source.split("# --- App ---")[1]

    def test_app_load_ok_shown_first(self):
        self.assertIn("앱 로딩 완료", self.app_source)
        load_idx = self.main_block.find("render_app_load_ok_html")
        history_idx = self.main_block.find("render_history_chips")
        ai_idx = self.main_block.find("run_ai_analysis")
        self.assertLess(load_idx, history_idx)
        self.assertLess(history_idx, ai_idx)

    def test_history_and_buttons_before_ai_analysis(self):
        history_idx = self.main_block.find("render_history_chips")
        buttons_idx = self.main_block.find("render_input_buttons")
        ai_idx = self.main_block.find("run_ai_analysis")
        self.assertLess(history_idx, ai_idx)
        self.assertLess(buttons_idx, ai_idx)

    def test_mobile_sticky_not_fixed_on_small_screens(self):
        self.assertIn("position: static !important", self.mobile_css)
        self.assertNotIn("z-index: 999", self.mobile_css)
        self.assertNotIn("100vh", self.mobile_css)

    def test_mobile_single_column_layout(self):
        self.assertIn("flex-direction: column !important", self.mobile_css)
        self.assertIn("width: 100% !important", self.mobile_css)

    def test_overflow_visible_on_main_container(self):
        self.assertIn("overflow-y: visible !important", self.mobile_css)
        self.assertIn("min-height: auto !important", self.mobile_css)

    def test_advanced_sections_have_error_guards(self):
        for label in ("EXP_BACKUP", "EXP_ADVANCED", "render_pattern_ranking"):
            self.assertIn(label, self.main_block)
        self.assertIn("_safe_section", self.main_block)
        self.assertIn("고급 설정을 표시할 수 없습니다", self.main_block)
        self.assertNotIn("st.exception", self.app_source)

    def test_render_app_load_ok_helper_exists(self):
        from mobile_ui import render_app_load_ok_html

        html = render_app_load_ok_html()
        self.assertIn("앱 로딩 완료", html)
        self.assertIn("app-load-ok", html)


if __name__ == "__main__":
    unittest.main()
