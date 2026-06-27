"""6-step protection mode — risk indicator only; never blocks prediction."""

from typing import Any, Dict, Tuple

PASS_MSG = "6단계 보호 모드 — 위험도 상향"


def _protection_risk_level(
    current_losing_streak: int,
    risk_level: str,
    confidence: float,
    road_agreement: float,
    min_conf: float,
) -> str:
    if current_losing_streak >= 4 or risk_level == "EXTREME":
        return "EXTREME"
    if current_losing_streak >= 3 or risk_level == "HIGH":
        return "HIGH"
    if (
        current_losing_streak >= 2
        or confidence < min_conf
        or road_agreement < 65
        or risk_level == "MEDIUM"
    ):
        return "MEDIUM"
    return "LOW"


def apply_protection_mode(
    confidence: float,
    risk_level: str,
    road_agreement: float,
    current_losing_streak: int,
    enabled: bool = True,
) -> Tuple[bool, float, Dict[str, Any]]:
    meta: Dict[str, Any] = {
        "enabled": enabled,
        "current_streak": current_losing_streak,
        "streak_risk": "LOW",
        "prediction_allowed": True,
        "min_confidence_required": 0.55,
        "risk_level": "LOW",
    }

    if not enabled:
        meta["risk_level"] = "LOW"
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
        meta["streak_risk"] = "EXTREME"
    if current_losing_streak >= 5:
        min_conf = 0.99

    meta["min_confidence_required"] = min_conf
    meta["risk_level"] = _protection_risk_level(
        current_losing_streak,
        risk_level,
        confidence,
        road_agreement,
        min_conf,
    )
    meta["streak_risk"] = meta["risk_level"]

    return False, min_conf, meta
