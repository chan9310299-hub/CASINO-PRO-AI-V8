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
        title_idx = self.main_block.find("render_v10_title_early")
        history_idx = self.main_block.find("render_history_chips")
        db_idx = self.main_block.find("get_storage_backend")
        self.assertLess(load_idx, title_idx)
        self.assertLess(title_idx, db_idx)
        self.assertLess(history_idx, self.main_block.find("run_ai_analysis"))

    def test_title_and_buttons_before_db_heavy_work(self):
        title_idx = self.main_block.find("render_v10_title_early")
        buttons_idx = self.main_block.find("render_input_buttons")
        ai_idx = self.main_block.find("run_ai_analysis")
        self.assertLess(title_idx, buttons_idx)
        self.assertLess(buttons_idx, ai_idx)

    def test_main_containers_forced_visible_on_mobile(self):
        self.assertIn("visibility: visible !important", self.mobile_css)
        self.assertIn("[data-testid=\"stAppViewContainer\"]", self.mobile_css)
        self.assertIn("overflow-y: visible !important", self.mobile_css)

    def test_no_footer_or_main_hiding_on_mobile(self):
        self.assertNotIn("footer { visibility: hidden", self.mobile_css)
        self.assertNotIn("footer, [data-testid", self.mobile_css)
        self.assertNotIn("opacity: 0 !important", self.mobile_css)
        self.assertNotIn("100vh", self.mobile_css)
        self.assertNotIn("position: fixed", self.mobile_css)
        self.assertNotIn("footer, .stDeployButton { visibility: hidden", self.app_source)

    def test_no_sticky_or_fixed_layers_on_mobile(self):
        self.assertIn("position: static !important", self.mobile_css)
        self.assertNotIn("position: sticky", self.mobile_css.replace("position: static !important", ""))
        self.assertNotIn("z-index: 999", self.mobile_css)
        self.assertNotIn("z-index: 998", self.mobile_css)

    def test_mobile_single_column_layout(self):
        self.assertIn("flex-direction: column !important", self.mobile_css)
        self.assertIn("width: 100% !important", self.mobile_css)

    def test_advanced_sections_have_error_guards(self):
        self.assertIn("_safe_section", self.main_block)
        self.assertIn("고급 설정을 표시할 수 없습니다", self.main_block)
        self.assertNotIn("st.exception", self.app_source)

    def test_render_app_load_ok_helper_exists(self):
        from mobile_ui import render_app_load_ok_html
        from ui_ko import APP_LOAD_OK

        html = render_app_load_ok_html()
        self.assertIn(APP_LOAD_OK, html)
        self.assertIn("app-load-ok", html)

    def test_early_title_helper_exists(self):
        from v10_ui import render_v10_title_early

        html = render_v10_title_early()
        self.assertIn("CASINO PRO AI", html)


if __name__ == "__main__":
    unittest.main()
