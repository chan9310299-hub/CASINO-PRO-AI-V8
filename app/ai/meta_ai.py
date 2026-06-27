"""Meta AI — weighted voter fusion — CASINO PRO AI v6."""

from typing import Any, Dict, List, Optional

from ai.confidence_v6 import compute_dynamic_confidence, voter_agreement_pct
from ai.voting_engine import combine_votes


def _voter_weight(db, voter_name: str, default: float) -> float:
    if db is None:
        return default
    weights = db.get_all_signal_weights()
    key_map = {
        "trend_ai": "recent_20",
        "road_ai": "bigroad",
        "pattern_ai": "pattern_memory",
        "memory_ai": "dragon",
        "risk_ai": "chop",
    }
    key = key_map.get(voter_name, voter_name)
    return weights.get(key, default)


def meta_ai_vote(
    history: List[str],
    base_result: Dict[str, Any],
    pattern_similarity: Dict[str, Any],
    data_counts: Optional[Dict[str, Any]],
    db=None,
) -> Dict[str, Any]:
    voting = combine_votes(history, base_result, pattern_similarity, data_counts)
    voters = voting["voters"]

    for voter in voters:
        base_w = voter.get("weight", 1.0)
        adaptive = _voter_weight(db, voter["name"], base_w)
        if voter.get("confidence", 0) < 0.45:
            voter["weight"] = adaptive * 0.5
        else:
            voter["weight"] = adaptive

    p_score = 0.0
    b_score = 0.0
    for voter in voters:
        if voter.get("vote") not in ("P", "B"):
            continue
        if voter.get("confidence", 0) < 0.40:
            continue
        w = voter["weight"] * voter["confidence"]
        if voter["vote"] == "P":
            p_score += w
        else:
            b_score += w

    if p_score + b_score <= 0:
        p_score = voting["weighted_p_score"]
        b_score = voting["weighted_b_score"]

    total = p_score + b_score
    probability_p = round(p_score / total, 4) if total else 0.5
    probability_b = round(b_score / total, 4) if total else 0.5
    prediction = "P" if probability_p >= probability_b else "B"
    raw_conf = max(probability_p, probability_b)

    v_agree = voter_agreement_pct(voters)
    sample_size = pattern_similarity.get("sample_size", 0) + len(
        [x for x in history if x in ("P", "B")]
    )
    acc = (data_counts or {}).get("ai_accuracy_pct", 0.0)

    confidence = compute_dynamic_confidence(
        raw_conf,
        sample_size,
        road_agreement_pct=0.0,
        pattern_similarity_pct=pattern_similarity.get("similarity_percent", 0),
        signal_agreement=0.5,
        trend_consistency=0.5,
        recent_accuracy_pct=acc,
        voter_agreement_pct=v_agree,
    )

    meta_score = round((probability_p if prediction == "P" else probability_b) * confidence, 4)

    return {
        "prediction": prediction,
        "confidence": confidence,
        "probability_p": probability_p,
        "probability_b": probability_b,
        "voters": voters,
        "meta_score": meta_score,
        "weighted_p_score": round(p_score, 4),
        "weighted_b_score": round(b_score, 4),
    }
