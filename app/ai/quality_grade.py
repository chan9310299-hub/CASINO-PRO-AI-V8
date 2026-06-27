"""Quality grading and safe AI defaults."""

from typing import Any, Dict, List, Optional

INSUFFICIENT_MSG = "데이터 부족 - 관망 권장"


def calibrate_confidence(
    raw: float,
    resolved_count: int,
    recent_accuracy_pct: float = 0.0,
) -> float:
    raw = max(0.0, min(1.0, raw))
    sample_factor = min(1.0, resolved_count / 50.0)
    acc_bias = (recent_accuracy_pct - 50.0) / 300.0 if resolved_count >= 5 else 0.0
    calibrated = raw * (0.82 + 0.18 * sample_factor) + acc_bias
    return round(max(0.0, min(0.99, calibrated)), 4)


def detect_unstable_pattern(
    pb_count: int,
    trend_stability: float,
    signal_conflict: float,
) -> bool:
    if pb_count < 8:
        return True
    if trend_stability < 0.35:
        return True
    if signal_conflict >= 0.45:
        return True
    return False


def grade_prediction(
    confidence: float,
    risk_level: str,
    road_agreement: float,
    is_low_confidence: bool = False,
) -> str:
    if is_low_confidence or risk_level in ("HIGH", "EXTREME"):
        return "C"
    if confidence >= 0.82 and road_agreement >= 75 and risk_level == "LOW":
        return "A"
    if confidence >= 0.68 and road_agreement >= 60:
        return "B"
    return "C"


def smooth_probabilities(p: float, b: float, alpha: float = 0.15) -> Dict[str, float]:
    p = max(0.0, min(1.0, p))
    b = max(0.0, min(1.0, b))
    total = p + b
    if total <= 0:
        return {"P": 0.5, "B": 0.5}
    raw_p, raw_b = p / total, b / total
    smooth_p = raw_p * (1 - alpha) + 0.5 * alpha
    smooth_b = raw_b * (1 - alpha) + 0.5 * alpha
    norm = smooth_p + smooth_b
    return {"P": round(smooth_p / norm, 4), "B": round(smooth_b / norm, 4)}


def cold_start_mode(pb_count: int, resolved_count: int) -> bool:
    if pb_count < 8:
        return True
    if pb_count < 12 and resolved_count < 5:
        return True
    if resolved_count < 3 and pb_count < 20:
        return True
    return False


def safe_ai_result(**overrides) -> Dict[str, Any]:
    base = {
        "prediction": None,
        "confidence": 0.0,
        "weighted_score": {"P": 0.0, "B": 0.0},
        "score": {"P": 0.0, "B": 0.0},
        "signal_breakdown": {},
        "reason_in_korean": [INSUFFICIENT_MSG],
        "reason": [INSUFFICIENT_MSG],
        "status": INSUFFICIENT_MSG,
        "learned_weights": {},
        "probability_p": 0.5,
        "probability_b": 0.5,
        "voters": [],
        "pattern_similarity": {},
        "data_counts": {},
        "v6_dashboard": {},
        "quality_grade": "C",
        "low_confidence": True,
        "pass_flag": False,
        "risk_level": "LOW",
        "road_agreement": 0.0,
        "protection_mode": {},
        "performance": {},
    }
    base.update(overrides)
    return base


def get_field(data: Optional[dict], key: str, default=None):
    if not isinstance(data, dict):
        return default
    return data.get(key, default)
