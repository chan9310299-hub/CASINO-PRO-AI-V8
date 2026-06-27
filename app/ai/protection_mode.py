"""6-step protection mode — reduces exposure, not guaranteed prevention."""

from typing import Any, Dict, Tuple

PASS_MSG = "6단계 보호 모드 — 통계적 예측 차단"


def apply_protection_mode(
    confidence: float,
    risk_level: str,
    road_agreement: float,
    current_losing_streak: int,
    enabled: bool = True,
) -> Tuple[bool, float, Dict[str, Any]]:
    meta = {
        "enabled": enabled,
        "current_streak": current_losing_streak,
        "streak_risk": "LOW",
        "prediction_allowed": True,
        "min_confidence_required": 0.55,
    }

    if not enabled:
        return False, 0.55, meta

    min_conf = 0.55
    if current_losing_streak >= 2:
        min_conf = 0.70
        meta["streak_risk"] = "MEDIUM"
    if current_losing_streak >= 3:
        min_conf = 0.90
        meta["streak_risk"] = "HIGH"
    if current_losing_streak >= 4:
        min_conf = 0.98
        meta["streak_risk"] = "CRITICAL"
    if current_losing_streak >= 5:
        min_conf = 0.99

    meta["min_confidence_required"] = min_conf

    if risk_level in ("HIGH", "EXTREME"):
        meta["prediction_allowed"] = False
        return True, min_conf, meta

    if road_agreement < 65:
        meta["prediction_allowed"] = False
        return True, min_conf, meta

    if confidence < min_conf:
        meta["prediction_allowed"] = False
        return True, min_conf, meta

    if current_losing_streak >= 4 and confidence < 0.98:
        meta["prediction_allowed"] = False
        return True, min_conf, meta

    return False, min_conf, meta
