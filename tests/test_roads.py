import sys
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP_DIR))

from road_engine import RoadEngine
from derived_road import build_big_eye, build_small_road, build_cockroach_road
from bigroad import BigRoadEngine


class BigRoadTests(unittest.TestCase):

    def test_first_streak_stacks_down(self):
        road = RoadEngine(["P", "P", "P"]).build_bigroad()
        self.assertEqual(
            [(c["row"], c["col"], c["result"]) for c in road],
            [(0, 0, "P"), (1, 0, "P"), (2, 0, "P")],
        )

    def test_streak_change_new_column(self):
        road = RoadEngine(["P", "B", "B"]).build_bigroad()
        self.assertEqual(
            [(c["row"], c["col"], c["result"]) for c in road],
            [(0, 0, "P"), (0, 1, "B"), (1, 1, "B")],
        )

    def test_tie_increments_last_cell(self):
        road = RoadEngine(["P", "T", "T"]).build_bigroad()
        self.assertEqual(len(road), 1)
        self.assertEqual(road[0]["ties"], 2)

    def test_first_hand_tie_then_player(self):
        road = RoadEngine(["T", "P"]).build_bigroad()
        self.assertEqual(len(road), 1)
        self.assertEqual(road[0]["row"], 0)
        self.assertEqual(road[0]["col"], 0)
        self.assertEqual(road[0]["ties"], 1)
        self.assertEqual(road[0]["result"], "P")

    def test_dragon_tail_at_sixth_row(self):
        road = RoadEngine(["P"] * 7).build_bigroad()
        positions = [(c["row"], c["col"]) for c in road]
        self.assertIn((5, 0), positions)
        self.assertIn((5, 1), positions)

    def test_bigroad_engine_wrapper(self):
        engine = BigRoadEngine()
        engine.load(["B", "P"])
        road = engine.build()
        self.assertEqual(len(road), 2)


class BigEyeTests(unittest.TestCase):

    def test_starts_after_second_column_opens(self):
        marks = build_big_eye(["P", "B"])["marks"]
        self.assertEqual(marks, [])

        marks = build_big_eye(["P", "B", "P"])["marks"]
        self.assertEqual(len(marks), 1)

    def test_new_column_equal_depth_is_red(self):
        # col0 depth 1, col1 depth 1 when col2 opens
        marks = build_big_eye(["P", "B", "P"])["marks"]
        self.assertEqual(marks[0], "R")

    def test_new_column_different_depth_is_blue(self):
        marks = build_big_eye(["P", "B", "B", "P"])["marks"]
        # hand3 B stacks (1,1); hand4 P opens col2: depths 2 vs 1
        self.assertEqual(marks[0], "B")
        self.assertEqual(marks[1], "B")

    def test_depth_entry_compares_cell_content(self):
        # P B B: at (1,1) left=(1,0) empty, above-left=(0,0)=P -> Blue
        marks = build_big_eye(["P", "B", "B"])["marks"]
        self.assertEqual(marks[0], "B")

    def test_tie_after_start_adds_mark(self):
        marks = build_big_eye(["P", "B", "T"])["marks"]
        self.assertEqual(len(marks), 1)

    def test_mark_count_vs_bigroad(self):
        history = ["P", "B", "P", "B", "P", "B", "P"]
        bigroad = RoadEngine(history).build_bigroad()
        marks = build_big_eye(history)["marks"]
        first_col_len = sum(1 for c in bigroad if c["col"] == 0)
        self.assertEqual(len(marks), len(history) - first_col_len - 1)


class SmallRoadTests(unittest.TestCase):

    def test_starts_after_third_column(self):
        self.assertEqual(build_small_road(["P", "B", "P"])["marks"], [])
        self.assertEqual(len(build_small_road(["P", "B", "P", "B"])["marks"]), 1)

    def test_new_column_uses_col_minus_three(self):
        marks = build_small_road(["P", "B", "P", "B"])["marks"]
        self.assertEqual(marks[0], "R")


class CockroachTests(unittest.TestCase):

    def test_starts_after_fourth_column(self):
        history = ["P", "B", "P", "B", "P"]
        self.assertEqual(build_cockroach_road(history[:4])["marks"], [])
        self.assertEqual(len(build_cockroach_road(history)["marks"]), 1)

    def test_new_column_uses_col_minus_four(self):
        marks = build_cockroach_road(["P", "B", "P", "B", "P"])["marks"]
        self.assertEqual(marks[0], "R")


class DerivedGridTests(unittest.TestCase):

    def test_grid_stacks_same_color_vertically(self):
        grid = build_big_eye(["P", "B", "P", "B"])["grid"]
        marks = [cell["mark"] for cell in grid]
        rows = [cell["row"] for cell in grid]
        self.assertEqual(marks, ["R", "R"])
        self.assertEqual(rows, [0, 1])

    def test_grid_new_column_on_color_change(self):
        grid = build_big_eye(["P", "B", "B", "B"])["grid"]
        marks = [cell["mark"] for cell in grid]
        cols = [cell["col"] for cell in grid]
        self.assertEqual(marks, ["B", "R"])
        self.assertEqual(cols, [0, 1])


if __name__ == "__main__":
    unittest.main()
