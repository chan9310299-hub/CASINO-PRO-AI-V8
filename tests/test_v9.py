import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

APP_DIR = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP_DIR))

from database import Database
from storage import Storage, backup_db, load_ai_stats, load_history, save_history
from access_guard import get_configured_access_code, is_access_granted
from mobile_ui import (
    CLOUD_BACKUP_WARNING,
    MOBILE_CSS,
    mobile_pro_close,
    mobile_pro_open,
    render_cloud_warning_html,
    sticky_input_close,
    sticky_input_open,
)
from ai.v9_signals import (
    V9_SIGNAL_NAMES,
    anti_six_loss_ai,
    chop_ai,
    collect_v9_signals,
    dragon_ai,
    memory_similarity_ai,
    meta_vote_ai,
    reversal_ai,
    risk_filter_ai,
    road_consensus_ai,
    signal_to_voter,
    streak_ai,
    two_side_balance_ai,
)
from ai.final_prediction import (
    LOW_CONFIDENCE_CAP,
    apply_low_confidence,
    assert_final_prediction,
    compute_expected_hit_rate,
    confidence_label,
    resolve_weighted_prediction,
    tie_break_prediction,
)
from ai.meta_vote_v9 import meta_vote_v9_decide

MIN_SAMPLE_SIZE = 8


class V9SignalsTest(unittest.TestCase):
    def _assert_signal_shape(self, sig):
        self.assertIn(sig["prediction"], ("P", "B", "PASS"))
        self.assertIn("confidence", sig)
        self.assertIn("reason", sig)
        self.assertIn("risk_level", sig)
        self.assertIn(sig["risk_level"], ("LOW", "MEDIUM", "HIGH", "EXTREME"))

    def test_all_v9_signal_names(self):
        self.assertEqual(len(V9_SIGNAL_NAMES), 10)

    def test_streak_ai_pass_short(self):
        sig = streak_ai(["P", "B", "P"])
        self._assert_signal_shape(sig)
        self.assertEqual(sig["prediction"], "PASS")

    def test_streak_ai_long_streak(self):
        sig = streak_ai(["P"] * 5)
        self._assert_signal_shape(sig)
        self.assertEqual(sig["prediction"], "P")
        self.assertGreater(sig["confidence"], 0.5)

    def test_chop_ai_pass_insufficient(self):
        sig = chop_ai(["P", "B", "P"])
        self.assertEqual(sig["prediction"], "PASS")

    def test_chop_ai_alternating(self):
        sig = chop_ai(["P", "B", "P", "B", "P", "B"])
        self._assert_signal_shape(sig)
        self.assertIn(sig["prediction"], ("P", "B"))

    def test_dragon_ai(self):
        sig = dragon_ai(["B"] * 5)
        self._assert_signal_shape(sig)
        self.assertEqual(sig["prediction"], "B")

    def test_reversal_ai_long_streak(self):
        sig = reversal_ai(["P"] * 8)
        self._assert_signal_shape(sig)
        self.assertEqual(sig["prediction"], "B")

    def test_two_side_balance_p_heavy(self):
        sig = two_side_balance_ai(["P"] * 12 + ["B"] * 3)
        self._assert_signal_shape(sig)
        self.assertEqual(sig["prediction"], "B")

    def test_road_consensus_ai(self):
        sig = road_consensus_ai({"weighted_score": {"P": 8, "B": 2}})
        self._assert_signal_shape(sig)
        self.assertEqual(sig["prediction"], "P")

    def test_memory_similarity_ai(self):
        sig = memory_similarity_ai({
            "similarity_percent": 75,
            "sample_size": 5,
            "p_probability": 0.6,
            "b_probability": 0.4,
        })
        self._assert_signal_shape(sig)
        self.assertEqual(sig["prediction"], "P")

    def test_risk_filter_high_risk(self):
        sig = risk_filter_ai("HIGH", 0.7)
        self.assertEqual(sig["prediction"], "PASS")

    def test_risk_filter_low_confidence(self):
        sig = risk_filter_ai("LOW", 0.4)
        self.assertEqual(sig["prediction"], "PASS")

    def test_meta_vote_ai_clear_winner(self):
        voters = [
            {"vote": "P", "weight": 1.0, "confidence": 0.8},
            {"vote": "P", "weight": 1.0, "confidence": 0.7},
            {"vote": "B", "weight": 1.0, "confidence": 0.3},
        ]
        sig = meta_vote_ai(voters)
        self._assert_signal_shape(sig)
        self.assertEqual(sig["prediction"], "P")

    def test_anti_six_loss_protection(self):
        sig = anti_six_loss_ai(4, protection_enabled=True)
        self.assertEqual(sig["prediction"], "PASS")
        self.assertIn("HIGH", sig["risk_level"])

    def test_anti_six_loss_off(self):
        sig = anti_six_loss_ai(5, protection_enabled=False)
        self.assertEqual(sig["prediction"], "PASS")

    def test_collect_v9_signals_count(self):
        pb = ["P", "B", "P", "B", "P", "B", "P", "B", "P", "B"]
        signals = collect_v9_signals(
            pb,
            base_result={"weighted_score": {"P": 5, "B": 3}},
            pattern_sim={"similarity_percent": 60, "sample_size": 4, "p_probability": 0.55, "b_probability": 0.45},
            current_streak=1,
            risk_level="LOW",
            confidence=0.6,
            voters=[{"vote": "P", "weight": 1.0, "confidence": 0.6}],
            protection_enabled=True,
        )
        self.assertEqual(len(signals), 10)
        for sig in signals:
            self._assert_signal_shape(sig)

    def test_signal_to_voter_pass(self):
        voter = signal_to_voter({
            "name": "streak_ai",
            "prediction": "PASS",
            "confidence": 0.5,
            "reason": "test",
            "risk_level": "LOW",
        })
        self.assertIsNone(voter["vote"])
        self.assertEqual(voter["name"], "streak_ai")


class MetaVoteV9Test(unittest.TestCase):
    def _voter(self, name, vote, conf=0.8):
        return {"name": name, "vote": vote, "confidence": conf, "weight": 1.0}

    def _assert_final_pb(self, result):
        self.assertIn(result["prediction"], ("P", "B"))
        self.assertNotEqual(result["prediction"], "PASS")

    def test_small_sample_low_confidence(self):
        result = meta_vote_v9_decide(
            existing_voters=[self._voter("trend_ai", "P")],
            v9_signals=[],
            sample_size=MIN_SAMPLE_SIZE - 1,
        )
        self._assert_final_pb(result)
        self.assertTrue(result["low_confidence"])
        self.assertLessEqual(result["confidence"], LOW_CONFIDENCE_CAP)

    def test_strong_conflict_still_predicts(self):
        voters = [self._voter("a", "P"), self._voter("b", "B")] * 5
        result = meta_vote_v9_decide(
            existing_voters=voters,
            v9_signals=[],
            sample_size=20,
        )
        self._assert_final_pb(result)
        self.assertTrue(result["low_confidence"])

    def test_protection_mode_low_confidence_not_block(self):
        result = meta_vote_v9_decide(
            existing_voters=[self._voter("trend_ai", "P", 0.9)],
            v9_signals=[],
            sample_size=20,
            protection_mode_enabled=True,
            prot_meta={"risk_level": "EXTREME"},
        )
        self._assert_final_pb(result)
        self.assertTrue(result["low_confidence"])

    def test_clear_p_prediction(self):
        voters = [self._voter("trend_ai", "P", 0.9)] * 4
        result = meta_vote_v9_decide(
            existing_voters=voters,
            v9_signals=[],
            sample_size=20,
            protection_mode_enabled=False,
            prot_meta={"risk_level": "LOW"},
        )
        self.assertEqual(result["prediction"], "P")
        self.assertIn(result["quality_grade"], ("A", "B", "C"))
        self.assertIn("expected_hit_rate", result)

    def test_voter_summary_present(self):
        result = meta_vote_v9_decide(
            existing_voters=[self._voter("trend_ai", "B", 0.85)],
            v9_signals=[{
                "name": "streak_ai",
                "prediction": "B",
                "confidence": 0.7,
                "reason": "streak",
                "risk_level": "LOW",
            }],
            sample_size=15,
            protection_mode_enabled=False,
            prot_meta={"risk_level": "LOW"},
        )
        self._assert_final_pb(result)
        self.assertGreaterEqual(len(result["voters"]), 2)
        self.assertIn("reasons", result)


class FinalPredictionHelpersTest(unittest.TestCase):
    def test_tie_break_memory(self):
        pred = tie_break_prediction(
            ["P", "B"],
            {"weighted_score": {"P": 1, "B": 1}},
            {"p_probability": 0.7, "b_probability": 0.3},
        )
        self.assertEqual(pred, "P")

    def test_resolve_always_pb(self):
        pred, conf, _, _ = resolve_weighted_prediction(0, 0, ["B", "B"], {"weighted_score": {"P": 0, "B": 0}})
        self.assertIn(pred, ("P", "B"))

    def test_low_confidence_cap(self):
        self.assertLessEqual(apply_low_confidence(0.85, True), LOW_CONFIDENCE_CAP)

    def test_expected_hit_rate(self):
        hit = compute_expected_hit_rate(0.72, 0.72, 0.28, "P")
        self.assertGreaterEqual(hit, 70)

    def test_confidence_label(self):
        self.assertEqual(confidence_label(0.88), "Very High")
        self.assertEqual(confidence_label(0.75), "High")
        self.assertEqual(confidence_label(0.55), "Medium")

    def test_assert_final_rejects_pass(self):
        with self.assertRaises(ValueError):
            assert_final_prediction("PASS")


class StorageWrapperTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "test.db")
        self._patches = [
            mock.patch("config.DB_PATH", Path(self.db_path)),
            mock.patch("database.DB_PATH", Path(self.db_path)),
            mock.patch("storage.DB_PATH", Path(self.db_path)),
        ]
        for p in self._patches:
            p.start()
        self.db = Database()
        self.storage = Storage(self.db)

    def tearDown(self):
        self.db.close()
        for p in self._patches:
            p.stop()
        self._tmpdir.cleanup()

    def test_load_save_history(self):
        self.storage.save_history("P")
        self.storage.save_history("B")
        hist = self.storage.load_history()
        self.assertEqual(hist, ["P", "B"])

    def test_module_load_history(self):
        save_history("T", self.db)
        self.assertEqual(load_history(self.db), ["T"])

    def test_load_ai_stats(self):
        stats = load_ai_stats(self.db)
        self.assertIn("total_predictions", stats)

    def test_backup_db(self):
        self.storage.save_history("P")
        with mock.patch("storage.backup_database") as mock_backup:
            mock_backup.return_value = Path(self.db_path)
            path = backup_db("manual", self.db)
            self.assertIsNotNone(path)
            mock_backup.assert_called_once()


class AccessGuardTest(unittest.TestCase):
    def test_no_access_code_grants_access(self):
        with mock.patch("access_guard.get_configured_access_code", return_value=""):
            self.assertTrue(is_access_granted())

    def test_configured_code_requires_session(self):
        with mock.patch("access_guard.get_configured_access_code", return_value="secret"):
            with mock.patch("access_guard.st") as mock_st:
                mock_st.session_state = {}
                self.assertFalse(is_access_granted())

    def test_get_configured_access_code_empty_on_error(self):
        with mock.patch("access_guard.st") as mock_st:
            mock_st.secrets.get.side_effect = Exception("no secrets")
            self.assertEqual(get_configured_access_code(), "")


class MobileLayoutHelpersTest(unittest.TestCase):
    def test_mobile_css_has_sticky(self):
        self.assertIn("sticky-input-wrap", MOBILE_CSS)

    def test_mobile_pro_stack_helpers(self):
        self.assertIn("mobile-pro-stack", mobile_pro_open())
        self.assertEqual(mobile_pro_close(), "</div>")

    def test_sticky_input_helpers(self):
        self.assertIn("sticky-input-wrap", sticky_input_open())
        self.assertEqual(sticky_input_close(), "</div>")

    def test_cloud_warning_text(self):
        self.assertIn("무료 클라우드", CLOUD_BACKUP_WARNING)
        html_out = render_cloud_warning_html()
        self.assertIn("cloud-warn", html_out)
        self.assertNotIn("<script", html_out)


if __name__ == "__main__":
    unittest.main()
