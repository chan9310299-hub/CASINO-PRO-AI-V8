"""
Backward-compatible facade for the unified prediction engine.

CASINO PRO AI v7: Production Hardened Edition.
"""

from typing import Any, Dict, List, Optional

from ai.bad_pattern_detector import detect_bad_patterns
from ai.backtest_engine import run_all_backtests
from ai.confidence_v6 import compute_dynamic_confidence, voter_agreement_pct
from ai.data_stats import get_data_counts
from ai.losing_streak import compute_losing_streaks
from ai.meta_ai import meta_ai_vote
from ai.pass_system import PASS_MESSAGE, evaluate_pass
from ai.pattern_similarity import analyze_pattern_similarity
from ai.prediction_engine import PredictionEngine
from ai.protection_mode import PASS_MSG, apply_protection_mode
from ai.quality_grade import (
    INSUFFICIENT_MSG,
    calibrate_confidence,
    cold_start_mode,
    detect_unstable_pattern,
    grade_prediction,
    safe_ai_result,
    smooth_probabilities,
)
from ai.risk_controller import compute_risk_score
from ai.road_agreement import compute_road_agreement


def _trend_stability(pb: List[str]) -> float:
    if len(pb) < 4:
        return 0.5
    changes = sum(1 for i in range(len(pb) - 1) if pb[i] != pb[i + 1])
    return round(1.0 - changes / max(len(pb) - 1, 1), 4)


def _signal_conflicts(voters: List[Dict[str, Any]]) -> float:
    votes = [v["vote"] for v in voters if v.get("vote") in ("P", "B")]
    if len(votes) < 2:
        return 0.0
    p, b = votes.count("P"), votes.count("B")
    return round(min(p, b) / len(votes), 4)


def _prediction_quality(confidence: float, risk_level: str, is_pass: bool) -> str:
    if is_pass:
        return "PASS"
    if risk_level in ("HIGH", "EXTREME"):
        return "Danger"
    if confidence >= 0.75:
        return "Safe"
    if confidence >= 0.60:
        return "Moderate"
    return "Low"


class RoadmapAI:
    """Delegates to PredictionEngine; v4/v6/v7 compatible analyze() API."""

    def __init__(
        self,
        weights=None,
        pattern_memory_lookup=None,
        db=None,
        voting_engine=None,
        pattern_similarity_engine=None,
        **kwargs,
    ):
        self.db = db
        self.voting_engine = voting_engine
        self.pattern_similarity_engine = pattern_similarity_engine
        self._engine = PredictionEngine(
            weights=weights,
            pattern_memory_lookup=pattern_memory_lookup,
        )

    def analyze(
        self,
        history,
        bigroad=None,
        bigeye=None,
        smallroad=None,
        cockroach=None,
        db=None,
        protection_mode_enabled: bool = True,
    ):
        try:
            return self._analyze_impl(
                history,
                bigroad=bigroad,
                bigeye=bigeye,
                smallroad=smallroad,
                cockroach=cockroach,
                db=db,
                protection_mode_enabled=protection_mode_enabled,
            )
        except Exception:
            return safe_ai_result()

    def _analyze_impl(
        self,
        history,
        bigroad=None,
        bigeye=None,
        smallroad=None,
        cockroach=None,
        db=None,
        protection_mode_enabled: bool = True,
    ):
        history = history or []
        db = db if db is not None else self.db

        base = self._engine.analyze(
            history,
            bigroad=bigroad,
            bigeye=bigeye,
            smallroad=smallroad,
            cockroach=cockroach,
        )

        pattern_fn = self.pattern_similarity_engine or analyze_pattern_similarity
        data_counts = {}
        if db:
            try:
                data_counts = get_data_counts(db, history) or {}
            except Exception:
                data_counts = {}

        pattern_sim = {
            "prediction": None,
            "p_probability": 0.5,
            "b_probability": 0.5,
            "confidence": 0.0,
            "matched_patterns": [],
            "sample_size": 0,
            "similarity_percent": 0.0,
            "reason": ["패턴 표본 부족"],
            "shape_tags": [],
        }
        if db:
            try:
                pattern_sim = pattern_fn(history, db) or pattern_sim
            except Exception:
                pass

        ws = base.get("weighted_score") or {"P": 0.0, "B": 0.0}
        total = ws.get("P", 0) + ws.get("B", 0)
        base_p = round(ws["P"] / total, 4) if total else 0.5
        base_b = round(ws["B"] / total, 4) if total else 0.5
        v6_empty = {
            "probability_p": base_p,
            "probability_b": base_b,
            "voters": [],
            "pattern_similarity": pattern_sim,
            "data_counts": data_counts,
            "v6_dashboard": {},
            "quality_grade": "PASS",
            "protection_mode": {},
            "performance": {},
        }

        if base.get("prediction") is None:
            return {**base, **v6_empty}

        if db is None:
            return {**base, **v6_empty}

        pb = [x for x in history if x in ("P", "B")]
        resolved_count = data_counts.get("resolved_ai_predictions", 0)
        is_cold = cold_start_mode(len(pb), resolved_count)

        meta = meta_ai_vote(history, base, pattern_sim, data_counts, db=db)
        voters = meta.get("voters") or []
        road_agreement = compute_road_agreement(base, voters)
        bad = detect_bad_patterns(pb, base)

        resolved = []
        try:
            resolved = db.get_resolved_predictions_pb() or []
        except Exception:
            resolved = []
        streaks = compute_losing_streaks(resolved)
        current_streak = streaks["current_losing_streak"]

        v_agree = voter_agreement_pct(voters)
        sample_size = pattern_sim.get("sample_size", 0) + len(pb)
        sim_pct = pattern_sim.get("similarity_percent", 0.0)
        acc_pct = data_counts.get("ai_accuracy_pct", 0.0)
        conflict = _signal_conflicts(voters)
        trend = _trend_stability(pb)

        raw_confidence = compute_dynamic_confidence(
            meta.get("confidence", 0.5),
            sample_size,
            road_agreement,
            sim_pct,
            signal_agreement=1.0 - conflict,
            trend_consistency=trend,
            recent_accuracy_pct=acc_pct,
            voter_agreement_pct=v_agree,
        )
        confidence = calibrate_confidence(raw_confidence, resolved_count, acc_pct)

        risk = compute_risk_score(
            recent_accuracy_pct=acc_pct,
            road_agreement_pct=road_agreement,
            trend_stability=trend,
            pattern_similarity_pct=sim_pct,
            signal_conflicts=conflict,
            confidence=confidence,
            prediction_volatility=min(current_streak / 10.0, 1.0),
        )

        is_pass, pass_reason = evaluate_pass(
            confidence,
            risk["risk_level"],
            sim_pct,
            road_agreement,
            current_streak,
            bad,
        )

        prot_pass, _, prot_meta = apply_protection_mode(
            confidence,
            risk["risk_level"],
            road_agreement,
            current_streak,
            enabled=protection_mode_enabled,
        )
        if prot_pass and protection_mode_enabled:
            is_pass = True
            pass_reason = pass_reason or PASS_MSG

        if detect_unstable_pattern(len(pb), trend, conflict):
            if not is_pass:
                is_pass = True
                pass_reason = pass_reason or "불안정 패턴 — PASS"

        merged_reason = list(base.get("reason_in_korean") or base.get("reason") or [])
        if is_cold and INSUFFICIENT_MSG not in merged_reason:
            merged_reason.insert(0, INSUFFICIENT_MSG)
        for r in pattern_sim.get("reason") or []:
            if r not in merged_reason:
                merged_reason.append(r)
        if conflict >= 0.35:
            msg = f"신호 충돌 감지 ({round(conflict * 100)}%)"
            if msg not in merged_reason:
                merged_reason.append(msg)

        prediction = meta.get("prediction")
        status = base.get("status", "")
        quality = _prediction_quality(confidence, risk["risk_level"], is_pass)
        quality_grade = grade_prediction(confidence, risk["risk_level"], road_agreement, is_pass)

        if is_pass:
            prediction = "PASS"
            status = PASS_MESSAGE
            quality = "PASS"
            quality_grade = "PASS"
            if pass_reason and pass_reason not in merged_reason:
                merged_reason.insert(0, pass_reason)
        elif is_cold:
            prediction = "PASS"
            status = INSUFFICIENT_MSG
            is_pass = True
            quality = "PASS"
            quality_grade = "PASS"

        probs = smooth_probabilities(
            meta.get("probability_p", 0.5),
            meta.get("probability_b", 0.5),
        )

        backtests = {}
        try:
            backtests = run_all_backtests(resolved)
            for window, bt in backtests.items():
                if bt.get("sample_size", 0) > 0:
                    db.save_backtest_v6(int(window), bt)
        except Exception:
            pass

        pass_rate = 0.0
        try:
            pass_rate = db.get_v6_pass_rate()
        except Exception:
            pass

        safe_rate = round(100.0, 2) if not is_pass and quality == "Safe" else 0.0
        danger_rate = 100.0 if quality == "Danger" else 0.0

        v6_dashboard = {
            "current_losing_streak": current_streak,
            "average_losing_streak": streaks["average_losing_streak"],
            "maximum_losing_streak": streaks["maximum_losing_streak"],
            "pass_rate": pass_rate,
            "safe_prediction_rate": safe_rate,
            "danger_prediction_rate": danger_rate,
            "road_agreement_pct": road_agreement,
            "pattern_similarity_pct": sim_pct,
            "meta_ai_score": meta.get("meta_score", 0.0),
            "risk_level": risk["risk_level"],
            "prediction_quality": quality,
            "quality_grade": quality_grade,
            "total_hands_stored": data_counts.get("total_input_hands", 0),
            "prediction_history_count": data_counts.get("total_ai_predictions", 0),
            "pattern_memory_count": data_counts.get("pattern_memory_count", 0),
            "learning_samples": data_counts.get("resolved_ai_predictions", 0),
            "resolved_predictions": data_counts.get("resolved_ai_predictions", 0),
            "pending_predictions": 0,
            "optimization_count": 0,
            "backtests": backtests,
            "protection_mode": prot_meta,
        }
        try:
            v6_dashboard["pending_predictions"] = db.count_pending_predictions()
            v6_dashboard["optimization_count"] = db.count_optimizer_v6_runs()
        except Exception:
            pass

        try:
            hand_index = len(history) + 1
            db.insert_v6_metrics(hand_index, {
                "risk_score": risk["risk_score"],
                "risk_level": risk["risk_level"],
                "road_agreement": road_agreement,
                "pattern_similarity": sim_pct,
                "meta_score": meta.get("meta_score"),
                "pass_flag": is_pass,
                "losing_streak": current_streak,
                "prediction_quality": quality,
            })
        except Exception:
            pass

        return {
            **base,
            "prediction": prediction,
            "confidence": confidence,
            "probability_p": probs["P"],
            "probability_b": probs["B"],
            "voters": voters,
            "pattern_similarity": pattern_sim,
            "data_counts": data_counts,
            "reason_in_korean": merged_reason,
            "reason": merged_reason,
            "status": status,
            "v6_dashboard": v6_dashboard,
            "risk_level": risk["risk_level"],
            "risk_score": risk["risk_score"],
            "road_agreement": road_agreement,
            "pass_flag": is_pass,
            "meta_score": meta.get("meta_score"),
            "quality_grade": quality_grade,
            "protection_mode": prot_meta,
        }
