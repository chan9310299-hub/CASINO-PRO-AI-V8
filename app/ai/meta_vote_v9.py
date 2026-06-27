"""CASINO PRO AI v9 — Meta AI final decision engine (always P/B)."""

from typing import Any, Dict, List, Optional

from ai.final_prediction import (
    apply_low_confidence,
    compute_expected_hit_rate,
    confidence_label,
    resolve_weighted_prediction,
    tie_break_prediction,
)
from ai.quality_grade import grade_prediction
from ai.v9_signals import DEFAULT_V9_WEIGHTS, signal_to_voter


def _conflict_ratio(voters: List[Dict[str, Any]]) -> float:
    votes = [v.get("vote") for v in voters if v.get("vote") in ("P", "B")]
    if len(votes) < 2:
        return 0.0
    p, b = votes.count("P"), votes.count("B")
    return round(min(p, b) / len(votes), 4)


def _get_weight(db, name: str, default: float) -> float:
    if db is None:
        return default
    try:
        weights = db.get_all_signal_weights()
        return float(weights.get(name, default))
    except Exception:
        return default


def meta_vote_v9_decide(
    existing_voters: List[Dict[str, Any]],
    v9_signals: List[Dict[str, Any]],
    db=None,
    sample_size: int = 0,
    protection_mode_enabled: bool = True,
    prot_meta: Optional[Dict[str, Any]] = None,
    road_agreement: float = 0.0,
    risk_level: str = "LOW",
    history: Optional[List[str]] = None,
    base_result: Optional[Dict[str, Any]] = None,
    pattern_sim: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    prot_meta = prot_meta or {}
    base_result = base_result or {}
    history = history or []
    pattern_sim = pattern_sim or {}

    v9_voters = [signal_to_voter(s) for s in v9_signals]
    all_voters = list(existing_voters or []) + v9_voters

    reasons: List[str] = []
    low_confidence = False

    if sample_size < 8:
        low_confidence = True
        reasons.append(f"표본 {sample_size} < 8 — 저신뢰")

    conflict = _conflict_ratio(all_voters)
    if conflict >= 0.42:
        low_confidence = True
        reasons.append(f"신호 강한 충돌 ({round(conflict * 100)}%) — 저신뢰")

    prot_risk = prot_meta.get("risk_level", "LOW")
    if protection_mode_enabled and prot_risk in ("HIGH", "EXTREME"):
        low_confidence = True
        reasons.append(f"6단계 보호 — 위험도 {prot_risk}")

    for sig in v9_signals:
        if sig.get("name") == "anti_six_loss_ai" and sig.get("prediction") == "PASS":
            if sig.get("risk_level") in ("HIGH", "EXTREME") and protection_mode_enabled:
                low_confidence = True
                if sig.get("reason") not in reasons:
                    reasons.append(sig.get("reason", "연패 보호 — 저신뢰"))

    p_score = b_score = 0.0
    for voter in all_voters:
        vote = voter.get("vote")
        if vote not in ("P", "B"):
            continue
        name = voter.get("name", "")
        default_w = DEFAULT_V9_WEIGHTS.get(name, voter.get("weight", 1.0))
        w = _get_weight(db, name, default_w) * float(voter.get("confidence", 0.5))
        if float(voter.get("confidence", 0)) < 0.35:
            continue
        if vote == "P":
            p_score += w
        else:
            b_score += w

    prediction, confidence, prob_p, prob_b = resolve_weighted_prediction(
        p_score, b_score, history, base_result, pattern_sim,
    )

    if p_score + b_score <= 0:
        low_confidence = True
        reasons.append("유효 투표 없음 — 기본 분석 사용")

    confidence = apply_low_confidence(confidence, low_confidence)
    quality_grade = grade_prediction(confidence, risk_level, road_agreement, low_confidence)

    for v in all_voters:
        r = v.get("reason")
        if r and r not in reasons:
            reasons.append(r)

    expected_hit = compute_expected_hit_rate(confidence, prob_p, prob_b, prediction)

    return {
        "prediction": prediction,
        "confidence": confidence,
        "probability_p": prob_p,
        "probability_b": prob_b,
        "quality_grade": quality_grade,
        "confidence_label": confidence_label(confidence),
        "expected_hit_rate": expected_hit,
        "reasons": reasons,
        "voters": all_voters,
        "low_confidence": low_confidence,
        "pass_flag": low_confidence,
        "conflict_ratio": conflict,
        "meta_score": round(confidence * (prob_p if prediction == "P" else prob_b), 4),
    }
