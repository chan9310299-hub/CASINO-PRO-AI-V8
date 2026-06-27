"""Always resolve a final PLAYER/BANKER prediction — never PASS."""

from typing import Any, Dict, List, Optional, Tuple

LOW_CONFIDENCE_CAP = 0.599
LOW_CONFIDENCE_STATUS = "저신뢰 예측"


def confidence_label(confidence: float) -> str:
    if confidence >= 0.75:
        return "High"
    if confidence >= 0.55:
        return "Medium"
    return "Low"


def compute_expected_hit_rate(
    confidence: float,
    prob_p: float,
    prob_b: float,
    prediction: str,
) -> float:
    side_prob = prob_p if prediction == "P" else prob_b
    rate = max(confidence, side_prob)
    return round(min(0.99, rate) * 100, 1)


def tie_break_prediction(
    history: List[str],
    base_result: Dict[str, Any],
    pattern_sim: Optional[Dict[str, Any]] = None,
) -> str:
    pattern_sim = pattern_sim or {}
    p_prob = pattern_sim.get("p_probability", 0.5)
    b_prob = pattern_sim.get("b_probability", 0.5)
    if p_prob != b_prob:
        return "P" if p_prob > b_prob else "B"

    pb = [x for x in (history or []) if x in ("P", "B")]
    if pb:
        recent = pb[-10:]
        p_cnt, b_cnt = recent.count("P"), recent.count("B")
        if p_cnt != b_cnt:
            return "P" if p_cnt >= b_cnt else "B"
        if pb[-1] in ("P", "B"):
            return pb[-1]

    ws = (base_result or {}).get("weighted_score") or {"P": 0, "B": 0}
    p_w, b_w = ws.get("P", 0), ws.get("B", 0)
    if p_w != b_w:
        return "P" if p_w >= b_w else "B"

    return "P"


def resolve_weighted_prediction(
    p_score: float,
    b_score: float,
    history: List[str],
    base_result: Dict[str, Any],
    pattern_sim: Optional[Dict[str, Any]] = None,
) -> Tuple[str, float, float, float]:
    total = p_score + b_score
    if total <= 0:
        prediction = tie_break_prediction(history, base_result, pattern_sim)
        return prediction, 0.5, 0.5, 0.5

    prob_p = round(p_score / total, 4)
    prob_b = round(b_score / total, 4)
    if prob_p == prob_b:
        prediction = tie_break_prediction(history, base_result, pattern_sim)
    else:
        prediction = "P" if prob_p > prob_b else "B"
    confidence = round(max(prob_p, prob_b), 4)
    return prediction, confidence, prob_p, prob_b


def apply_low_confidence(
    confidence: float,
    is_low: bool,
) -> float:
    if is_low:
        return round(min(confidence, LOW_CONFIDENCE_CAP), 4)
    return confidence


def assert_final_prediction(prediction: Optional[str]) -> None:
    if prediction is not None and prediction not in ("P", "B"):
        raise ValueError(f"Final prediction must be P or B, got {prediction!r}")
