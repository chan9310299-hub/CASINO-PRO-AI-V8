import sys
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP_DIR))

from ui_ko import HOME_LAYOUT_ORDER


class DerivedRoadRemovedTests(unittest.TestCase):
    def setUp(self):
        self.app_source = (APP_DIR / "app.py").read_text(encoding="utf-8")
        self.mobile_css = (APP_DIR / "mobile_ui.py").read_text(encoding="utf-8")

    def test_no_render_derived_row(self):
        self.assertNotIn("render_derived_row", self.app_source)
        self.assertNotIn("render_circle_road_html_only", self.app_source)

    def test_no_bigeeye_small_cockroach_ui(self):
        ui_forbidden = (
            "빅아이",
            "👁 BigEye",
            "🔹 Small",
            "🪳 Cockroach",
            "derived-row",
            "derived-card",
            "mini-scroll",
            "render_derived_row",
        )
        for word in ui_forbidden:
            self.assertNotIn(word, self.app_source, msg=f"Found UI reference: {word}")

    def test_no_derived_css_in_app(self):
        self.assertNotIn(".derived-row", self.app_source)
        self.assertNotIn(".derived-card", self.app_source)
        self.assertNotIn(".mini-cell", self.app_source)

    def test_no_derived_css_in_mobile_ui(self):
        self.assertNotIn("derived-row", self.mobile_css)

    def test_layout_order_no_derived_roads(self):
        from ui_ko import HOME_LAYOUT_ORDER
        self.assertNotIn("derived_roads", HOME_LAYOUT_ORDER)
        big_idx = HOME_LAYOUT_ORDER.index("big_road")
        six_idx = HOME_LAYOUT_ORDER.index("six_grid")
        perf_idx = HOME_LAYOUT_ORDER.index("performance_summary")
        self.assertLess(big_idx, six_idx)
        self.assertLess(six_idx, perf_idx)

    def test_six_grid_after_big_road_in_source(self):
        main = self.app_source.split("# --- App ---")[1]
        big_idx = main.find("render_bigroad(bigroad)")
        six_idx = main.find("render_six_grid(history)")
        self.assertGreater(big_idx, 0)
        self.assertGreater(six_idx, big_idx)

    def test_ai_still_computes_derived_internally(self):
        self.assertIn("BigEyeRoad", self.app_source)
        self.assertIn("bigeye=bigeye", self.app_source)

    def test_version_v11(self):
        from local_config import VERSION
        self.assertIn("v11", VERSION)


if __name__ == "__main__":
    unittest.main()
