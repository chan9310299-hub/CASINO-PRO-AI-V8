import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

APP_DIR = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP_DIR))

from database import Database
from roadmap_ai import RoadmapAI
from ai.adaptive_learning import (
    LEARNING_SIGNAL_DEFAULTS,
    WEIGHT_MAX,
    WEIGHT_MIN,
    build_adaptive_weight_map,
    lookup_pattern_memory,
    update_weights_after_resolution,
    clamp_weight,
    adjust_weight_from_accuracy,
)
from ai_learning import process_new_hand
from test_ai import _build_inputs

REQUIRED_ADAPTIVE_METHODS = [
    "ensure_adaptive_learning_tables",
    "get_all_signal_weights",
    "initialize_default_signal_weights",
    "update_signal_weight",
    "update_signal_performance",
    "get_pattern_memory_count",
    "upsert_pattern_memory",
    "lookup_pattern_memory",
    "reset_ai_learning",
]


class AdaptiveLearningDatabaseTests(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "test.db")
        self._patches = [
            mock.patch("config.DB_PATH", self.db_path),
            mock.patch("database.DB_PATH", self.db_path),
        ]
        for p in self._patches:
            p.start()
        self.db = Database()

    def tearDown(self):
        self.db.close()
        for p in self._patches:
            p.stop()
        self._tmpdir.cleanup()

    def test_required_adaptive_methods_exist(self):
        for name in REQUIRED_ADAPTIVE_METHODS:
            self.assertTrue(
                hasattr(self.db, name) and callable(getattr(self.db, name)),
                f"Missing method: {name}",
            )

    def test_ensure_adaptive_learning_tables(self):
        conn = self.db.connect()
        cur = conn.cursor()
        for table in ("ai_signal_weights", "ai_pattern_memory"):
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            self.assertIsNotNone(cur.fetchone(), table)
        conn.close()
        weights = self.db.get_all_signal_weights()
        self.assertEqual(len(weights), len(LEARNING_SIGNAL_DEFAULTS))

    def test_initialize_default_signal_weights(self):
        self.db.reset_ai_learning()
        weights = self.db.get_all_signal_weights()
        for name, default in LEARNING_SIGNAL_DEFAULTS.items():
            self.assertAlmostEqual(weights[name], default)
            self.assertEqual(self.db.get_signal_weight(name)["total"], 0)

    def test_get_all_signal_weights(self):
        weights = self.db.get_all_signal_weights()
        self.assertIsInstance(weights, dict)
        self.assertIn("dragon", weights)
        self.assertIsInstance(weights["dragon"], float)

    def test_update_signal_weight(self):
        self.db.update_signal_weight(
            "dragon", weight=1.5, total=10, correct=7, wrong=3, accuracy=0.7
        )
        row = self.db.get_signal_weight("dragon")
        self.assertAlmostEqual(row["weight"], 1.5)
        self.assertEqual(row["total"], 10)
        self.assertEqual(row["correct"], 7)
        self.assertEqual(row["wrong"], 3)
        self.assertAlmostEqual(row["accuracy"], 0.7)

    def test_update_signal_performance_correct(self):
        signal = "dragon"
        start = self.db.get_signal_weight(signal)["weight"]
        for _ in range(31):
            self.db.update_signal_performance(signal, True)
        updated = self.db.get_signal_weight(signal)
        self.assertEqual(updated["total"], 31)
        self.assertEqual(updated["correct"], 31)
        self.assertGreater(updated["weight"], start)

    def test_update_signal_performance_wrong(self):
        signal = "chop"
        start = self.db.get_signal_weight(signal)["weight"]
        for _ in range(31):
            self.db.update_signal_performance(signal, False)
        updated = self.db.get_signal_weight(signal)
        self.assertEqual(updated["total"], 31)
        self.assertEqual(updated["wrong"], 31)
        self.assertLess(updated["weight"], start)

    def test_weight_clamp_min_max(self):
        self.assertEqual(clamp_weight(WEIGHT_MIN - 1), WEIGHT_MIN)
        self.assertEqual(clamp_weight(WEIGHT_MAX + 5), WEIGHT_MAX)
        low = adjust_weight_from_accuracy(WEIGHT_MIN, 0.0, 25)
        self.assertGreaterEqual(low, WEIGHT_MIN)
        high = adjust_weight_from_accuracy(WEIGHT_MAX, 1.0, 35)
        self.assertLessEqual(high, WEIGHT_MAX)

    def test_get_pattern_memory_count(self):
        self.assertEqual(self.db.get_pattern_memory_count(), 0)
        self.db.upsert_pattern_memory("PPBBPP", 6, "B")
        self.assertEqual(self.db.get_pattern_memory_count(), 1)

    def test_upsert_pattern_memory(self):
        key = "PPBBPP"
        self.db.upsert_pattern_memory(key, 6, "B")
        row = self.db.lookup_pattern_memory(key)
        self.assertEqual(row["total"], 1)
        self.assertEqual(row["next_b"], 1)

        self.db.upsert_pattern_memory(key, 6, "P")
        row = self.db.lookup_pattern_memory(key)
        self.assertEqual(row["total"], 2)
        self.assertAlmostEqual(row["p_rate"], 0.5)

    def test_lookup_pattern_memory(self):
        key = "PBPBPB"
        for _ in range(5):
            self.db.upsert_pattern_memory(key, 6, "P")

        row = self.db.lookup_pattern_memory(key)
        self.assertIsNotNone(row)
        self.assertEqual(row["total"], 5)
        self.assertIsNone(self.db.lookup_pattern_memory("NOTFOUND"))

    def test_pattern_memory_lookup_via_adaptive_layer(self):
        pb = list("PBPBPB")
        key = "PBPBPB"
        for _ in range(5):
            self.db.upsert_pattern_memory(key, 6, "P")

        mem = lookup_pattern_memory(self.db, pb)
        self.assertTrue(mem["active"])
        self.assertIn("PLAYER", mem["reason"])

    def test_reset_ai_learning_preserves_history(self):
        self.db.add_result("P")
        self.db.insert_prediction_history(
            hand_index=2,
            history_snapshot=["P"],
            prediction="P",
            confidence=0.5,
            weighted_score={"P": 1, "B": 0},
            signal_breakdown_json={},
            reason_json=["test"],
        )
        self.db.update_signal_performance("dragon", True)
        self.db.upsert_pattern_memory("PPBBBB", 6, "P")

        self.db.reset_ai_learning()

        self.assertEqual(self.db.get_results(), ["P"])
        self.assertEqual(self.db.count_all_predictions(), 1)
        self.assertEqual(self.db.get_pattern_memory_count(), 0)
        weights = self.db.get_all_signal_weights()
        self.assertAlmostEqual(
            weights["dragon"],
            LEARNING_SIGNAL_DEFAULTS["dragon"],
        )
        self.assertEqual(self.db.get_signal_weight("dragon")["total"], 0)

    def test_update_weights_from_resolution_uses_breakdown(self):
        pending = {
            "signal_breakdown_json": json.dumps({
                "dragon": {"active": True},
                "recent_10": {"active": True},
                "chop": {"active": False},
            }),
        }
        update_weights_after_resolution(self.db, pending, True)
        self.assertEqual(self.db.get_signal_weight("dragon")["total"], 1)
        self.assertEqual(self.db.get_signal_weight("recent_10")["total"], 1)
        self.assertEqual(self.db.get_signal_weight("chop")["total"], 0)


class AdaptiveLearningIntegrationTests(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "test.db")
        self._patches = [
            mock.patch("config.DB_PATH", self.db_path),
            mock.patch("database.DB_PATH", self.db_path),
        ]
        for p in self._patches:
            p.start()
        self.db = Database()

    def tearDown(self):
        self.db.close()
        for p in self._patches:
            p.stop()
        self._tmpdir.cleanup()

    def test_roadmap_ai_returns_learned_weights(self):
        history = ["P", "B"] * 4
        kwargs = _build_inputs(history)
        weights = build_adaptive_weight_map(self.db)
        result = RoadmapAI(
            weights=weights,
            pattern_memory_lookup=lambda pb: lookup_pattern_memory(self.db, pb),
        ).analyze(**kwargs)

        self.assertIn("learned_weights", result)
        self.assertIn("dragon", result["learned_weights"])
        self.assertIn("pattern_memory", result["learned_weights"])

    def test_empty_history_does_not_crash(self):
        weights = build_adaptive_weight_map(self.db)
        result = RoadmapAI(weights=weights).analyze(
            [],
            bigroad=[],
            bigeye=[],
            smallroad=[],
            cockroach=[],
        )
        self.assertIsNone(result["prediction"])
        self.assertIn("learned_weights", result)

    def test_ties_do_not_corrupt_pattern_memory(self):
        for r in ["P", "T", "B", "T", "P", "B", "P", "B"]:
            process_new_hand(self.db, r, lambda h: {"prediction": None})

        patterns = self.db.get_pattern_memory_count()
        conn = self.db.connect()
        cur = conn.cursor()
        cur.execute("SELECT pattern_key FROM ai_pattern_memory")
        keys = [row[0] for row in cur.fetchall()]
        conn.close()
        for key in keys:
            self.assertNotIn("T", key)
        self.assertGreaterEqual(patterns, 0)


if __name__ == "__main__":
    unittest.main()
