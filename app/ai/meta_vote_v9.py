"""CASINO PRO AI v9 — Meta AI final decision engine."""

from typing import Any, Dict, List, Optional

from ai.quality_grade import grade_prediction
from ai.v9_signals import DEFAULT_V9_WEIGHTS, signal_to_voter

MIN_SAMPLE_SIZE = 8
STRONG_CONFLICT_THRESHOLD = 0.42


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
) -> Dict[str, Any]:
    prot_meta = prot_meta or {}
    v9_voters = [signal_to_voter(s) for s in v9_signals]
    all_voters = list(existing_voters or []) + v9_voters

    reasons: List[str] = []
    is_pass = False

    if sample_size < MIN_SAMPLE_SIZE:
        is_pass = True
        reasons.append(f"표본 {sample_size} < {MIN_SAMPLE_SIZE} — PASS")

    conflict = _conflict_ratio(all_voters)
    if conflict >= STRONG_CONFLICT_THRESHOLD:
        is_pass = True
        reasons.append(f"신호 강한 충돌 ({round(conflict * 100)}%) — PASS")

    if protection_mode_enabled and not prot_meta.get("prediction_allowed", True):
        is_pass = True
        reasons.append("6단계 보호 모드 — PASS")

    for sig in v9_signals:
        if sig.get("name") == "anti_six_loss_ai" and sig.get("prediction") == "PASS":
            if sig.get("risk_level") in ("HIGH", "EXTREME") and protection_mode_enabled:
                is_pass = True
                if sig.get("reason") not in reasons:
                    reasons.append(sig.get("reason", "anti_six_loss PASS"))

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

    total = p_score + b_score
    if total <= 0:
        is_pass = True
        reasons.append("유효 투표 없음 — PASS")
        prediction = "PASS"
        confidence = 0.0
        prob_p = prob_b = 0.5
    else:
        prob_p = round(p_score / total, 4)
        prob_b = round(b_score / total, 4)
        prediction = "P" if prob_p >= prob_b else "B"
        confidence = round(max(prob_p, prob_b), 4)

    if is_pass:
        prediction = "PASS"
        quality_grade = "PASS"
    else:
        quality_grade = grade_prediction(confidence, risk_level, road_agreement, False)

    for v in all_voters:
        r = v.get("reason")
        if r and r not in reasons:
            reasons.append(r)

    return {
        "prediction": prediction,
        "confidence": confidence,
        "probability_p": prob_p if total > 0 else 0.5,
        "probability_b": prob_b if total > 0 else 0.5,
        "quality_grade": quality_grade,
        "reasons": reasons,
        "voters": all_voters,
        "pass_flag": is_pass,
        "conflict_ratio": conflict,
        "meta_score": round(confidence * (prob_p if prediction == "P" else prob_b), 4) if not is_pass else 0.0,
    }
