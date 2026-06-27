"""Risk Controller — CASINO PRO AI v6. Analysis only."""

from typing import Any, Dict, List


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def compute_risk_score(
    recent_accuracy_pct: float,
    road_agreement_pct: float,
    trend_stability: float,
    pattern_similarity_pct: float,
    signal_conflicts: float,
    confidence: float,
    prediction_volatility: float,
) -> Dict[str, Any]:
    acc_factor = 1.0 - _clamp01(recent_accuracy_pct / 100.0)
    road_factor = 1.0 - _clamp01(road_agreement_pct / 100.0)
    trend_factor = 1.0 - _clamp01(trend_stability)
    pattern_factor = 1.0 - _clamp01(pattern_similarity_pct / 100.0)
    conflict_factor = _clamp01(signal_conflicts)
    conf_factor = 1.0 - _clamp01(confidence)
    vol_factor = _clamp01(prediction_volatility)

    score = (
        acc_factor * 0.20
        + road_factor * 0.20
        + trend_factor * 0.15
        + pattern_factor * 0.15
        + conflict_factor * 0.15
        + conf_factor * 0.10
        + vol_factor * 0.05
    )
    score = round(_clamp01(score), 4)

    if score >= 0.75:
        level = "EXTREME"
    elif score >= 0.55:
        level = "HIGH"
    elif score >= 0.35:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {"risk_score": score, "risk_level": level}
