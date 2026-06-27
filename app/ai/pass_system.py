"""PASS system — CASINO PRO AI v6. Statistical analysis only."""

from typing import Any, Dict, Optional, Tuple

PASS_MESSAGE = "통계적으로 신뢰할 수 있는 예측 없음 (PASS)"


def evaluate_pass(
    confidence: float,
    risk_level: str,
    pattern_similarity_pct: float,
    road_agreement_pct: float,
    current_losing_streak: int,
    bad_pattern: Dict[str, Any],
    base_confidence_threshold: float = 0.55,
) -> Tuple[bool, Optional[str]]:
    if bad_pattern.get("recommend_pass"):
        return True, "불안정 패턴 감지 — PASS"

    if risk_level in ("HIGH", "EXTREME"):
        return True, f"리스크 {risk_level} — PASS"

    if pattern_similarity_pct < 70.0:
        return True, "패턴 유사도 70% 미만 — PASS"

    if road_agreement_pct < 60.0:
        return True, "로드 합의 60% 미만 — PASS"

    from ai.losing_streak import min_confidence_for_streak

    min_conf = max(base_confidence_threshold, min_confidence_for_streak(current_losing_streak))
    if confidence < min_conf:
        return True, f"신뢰도 {min_conf:.0%} 미만 — PASS"

    if confidence < base_confidence_threshold:
        return True, "신뢰도 임계값 미만 — PASS"

    return False, None
