import sys
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP_DIR))

from ui_ko import MOBILE_LAYOUT_ORDER


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
        self.assertNotIn("derived_roads", MOBILE_LAYOUT_ORDER)
        six_idx = MOBILE_LAYOUT_ORDER.index("six_grid")
        big_idx = MOBILE_LAYOUT_ORDER.index("big_road")
        perf_idx = MOBILE_LAYOUT_ORDER.index("performance")
        self.assertLess(six_idx, big_idx)
        self.assertLess(big_idx, perf_idx)

    def test_six_grid_directly_before_big_road_in_source(self):
        six_idx = self.app_source.find("render_six_grid(history)")
        big_idx = self.app_source.find("render_bigroad(bigroad)")
        self.assertGreater(six_idx, 0)
        self.assertGreater(big_idx, six_idx)
        between = self.app_source[six_idx:big_idx]
        self.assertNotIn("derived", between.lower())

    def test_ai_still_computes_derived_internally(self):
        self.assertIn("BigEyeRoad", self.app_source)
        self.assertIn("bigeye=bigeye", self.app_source)

    def test_version_v92(self):
        from local_config import VERSION
        self.assertIn("v9.2", VERSION)


if __name__ == "__main__":
    unittest.main()
