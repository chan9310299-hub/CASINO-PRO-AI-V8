"""Smarter confidence and expected hit rate — CASINO PRO AI v11."""

from typing import Any, Dict, Optional

from ai.final_prediction import LOW_CONFIDENCE_CAP

PROTECTION_WARNING = "위험 구간 — 신뢰도 낮음"

_RISK_HIT_PENALTY = {
    "LOW": 0.0,
    "MEDIUM": 0.04,
    "HIGH": 0.10,
    "EXTREME": 0.16,
}


def confidence_label(confidence: float) -> str:
    if confidence >= 0.85:
        return "Very High"
    if confidence >= 0.70:
        return "High"
    if confidence >= 0.50:
        return "Medium"
    return "Low"


def apply_protection_confidence_penalty(
    confidence: float,
    prot_meta: Optional[Dict[str, Any]],
    enabled: bool = True,
) -> float:
    if not enabled or not prot_meta:
        return confidence
    risk = str(prot_meta.get("risk_level") or "LOW").upper()
    streak = int(prot_meta.get("current_streak") or 0)
    penalty = _RISK_HIT_PENALTY.get(risk, 0.0)
    if streak >= 5:
        penalty = max(penalty, 0.18)
    elif streak >= 4:
        penalty = max(penalty, 0.14)
    elif streak >= 3:
        penalty = max(penalty, 0.10)
    elif streak >= 2:
        penalty = max(penalty, 0.06)
    return round(max(0.32, confidence - penalty), 4)


def compute_smart_expected_hit_rate(
    confidence: float,
    prob_p: float,
    prob_b: float,
    prediction: str,
    *,
    recent_accuracy_pct: float = 0.0,
    signal_agreement: float = 0.5,
    pattern_memory_strength: float = 0.0,
    road_consensus: float = 0.0,
    risk_level: str = "LOW",
    sample_size: int = 0,
    low_confidence: bool = False,
) -> float:
    side_prob = prob_p if prediction == "P" else prob_b
    base = max(confidence, side_prob)

    acc = max(0.0, min(1.0, recent_accuracy_pct / 100.0)) if recent_accuracy_pct else 0.52
    agree = max(0.0, min(1.0, signal_agreement))
    pattern = max(0.0, min(1.0, pattern_memory_strength / 100.0))
    road = max(0.0, min(1.0, road_consensus / 100.0))

    blend = (
        base * 0.34
        + acc * 0.22
        + agree * 0.16
        + pattern * 0.14
        + road * 0.14
    )
    blend -= _RISK_HIT_PENALTY.get(str(risk_level).upper(), 0.0)

    if sample_size < 8:
        blend = min(blend, 0.57)
    elif sample_size < 15:
        blend = min(blend, 0.72)
    if low_confidence:
        blend = min(blend, LOW_CONFIDENCE_CAP)
    if agree < 0.45:
        blend = min(blend, 0.62)
    if pattern_memory_strength < 20 and sample_size < 12:
        blend = min(blend, 0.65)

    return round(min(0.99, max(0.40, blend)) * 100, 1)
