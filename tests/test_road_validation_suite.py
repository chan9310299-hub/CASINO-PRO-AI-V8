"""
Comprehensive road validation suite (100+ deterministic cases).

Compares application road engines against expected outputs defined in
road_validation_cases.py (computed from the independent reference oracle).
"""

import sys
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(TESTS_DIR))

from road_engine import RoadEngine
from derived_road import build_big_eye, build_small_road, build_cockroach_road
from road_rules_reference import normalize_bigroad
from road_validation_cases import VALIDATION_CASES, CATEGORY_INDEX


def _production_bigroad(history):
    return normalize_bigroad(RoadEngine(history).build_bigroad())


def _production_outputs(history):
    return {
        "bigroad": _production_bigroad(history),
        "big_eye": tuple(build_big_eye(history)["marks"]),
        "small_road": tuple(build_small_road(history)["marks"]),
        "cockroach": tuple(build_cockroach_road(history)["marks"]),
    }


class RoadValidationSuite(unittest.TestCase):
    """Parametrized validation of all road engines across 100+ cases."""

    @classmethod
    def setUpClass(cls):
        cls.cases = VALIDATION_CASES
        if len(cls.cases) < 100:
            raise unittest.SkipTest(
                f"Expected at least 100 cases, found {len(cls.cases)}"
            )

    def test_minimum_case_count(self):
        self.assertGreaterEqual(len(self.cases), 100)

    def test_category_coverage(self):
        required = [
            "bigroad_placement",
            "tie_handling",
            "dragon",
            "ping_pong",
            "big_eye",
            "small_road",
            "cockroach",
        ]
        for category in required:
            self.assertGreater(
                len(CATEGORY_INDEX[category]),
                0,
                f"No cases for category {category}",
            )

    def test_all_cases_match_expected(self):
        failures = []

        for case in self.cases:
            case_id = case["id"]
            history = case["history"]
            actual = _production_outputs(history)

            checks = [
                ("bigroad", case["expected_bigroad"], actual["bigroad"]),
                ("big_eye", case["expected_big_eye"], actual["big_eye"]),
                ("small_road", case["expected_small_road"], actual["small_road"]),
                ("cockroach", case["expected_cockroach"], actual["cockroach"]),
            ]

            for road_name, expected, got in checks:
                if expected != got:
                    failures.append(
                        f"{case_id} [{case['category']}] {road_name}:\n"
                        f"  history={history}\n"
                        f"  expected={expected}\n"
                        f"  actual={got}"
                    )

        if failures:
            preview = "\n\n".join(failures[:5])
            extra = len(failures) - 5
            suffix = f"\n\n... and {extra} more failures" if extra > 0 else ""
            self.fail(f"{len(failures)} case(s) failed:\n\n{preview}{suffix}")


class RoadValidationByCategory(unittest.TestCase):
    """Run category-focused assertions with explicit per-case subTests."""

    def _run_category(self, category):
        cases = [c for c in VALIDATION_CASES if c["category"] == category]
        self.assertGreater(len(cases), 0, f"No cases for {category}")

        for case in cases:
            with self.subTest(case_id=case["id"], history=case["history"]):
                actual = _production_outputs(case["history"])
                self.assertEqual(actual["bigroad"], case["expected_bigroad"])
                self.assertEqual(actual["big_eye"], case["expected_big_eye"])
                self.assertEqual(actual["small_road"], case["expected_small_road"])
                self.assertEqual(actual["cockroach"], case["expected_cockroach"])


class BigRoadPlacementTests(RoadValidationByCategory):
    def test_bigroad_placement(self):
        self._run_category("bigroad_placement")


class TieHandlingTests(RoadValidationByCategory):
    def test_tie_handling(self):
        self._run_category("tie_handling")


class DragonTests(RoadValidationByCategory):
    def test_dragon(self):
        self._run_category("dragon")


class PingPongTests(RoadValidationByCategory):
    def test_ping_pong(self):
        self._run_category("ping_pong")


class BigEyeBoyTests(RoadValidationByCategory):
    def test_big_eye(self):
        self._run_category("big_eye")


class SmallRoadTests(RoadValidationByCategory):
    def test_small_road(self):
        self._run_category("small_road")


class CockroachPigTests(RoadValidationByCategory):
    def test_cockroach(self):
        self._run_category("cockroach")


class GeneratedCaseTests(RoadValidationByCategory):
    def test_generated(self):
        self._run_category("generated")


class ExplicitScenarioTests(unittest.TestCase):
    """Spot-check named scenarios with fully inlined expectations."""

    def test_ping_pong_four_pairs(self):
        history = ["P", "B", "P", "B", "P", "B", "P", "B"]
        actual = _production_outputs(history)
        self.assertEqual(
            actual["bigroad"],
            (
                (0, 0, "P", 0, False),
                (0, 1, "B", 0, False),
                (0, 2, "P", 0, False),
                (0, 3, "B", 0, False),
                (0, 4, "P", 0, False),
                (0, 5, "B", 0, False),
                (0, 6, "P", 0, False),
                (0, 7, "B", 0, False),
            ),
        )
        self.assertEqual(actual["big_eye"], ("R", "R", "R", "R", "R", "R"))

    def test_dragon_seven_player(self):
        history = ["P"] * 7
        actual = _production_outputs(history)
        self.assertEqual(
            actual["bigroad"],
            (
                (0, 0, "P", 0, False),
                (1, 0, "P", 0, False),
                (2, 0, "P", 0, False),
                (3, 0, "P", 0, False),
                (4, 0, "P", 0, False),
                (5, 0, "P", 0, False),
                (5, 1, "P", 0, False),
            ),
        )

    def test_first_tie_then_banker(self):
        history = ["T", "B"]
        actual = _production_outputs(history)
        self.assertEqual(
            actual["bigroad"],
            ((0, 0, "B", 1, False),),
        )


if __name__ == "__main__":
    unittest.main()
