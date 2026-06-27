"""Top analysis reasons with scores — CASINO PRO AI v10."""

from typing import Any, Dict, List, Optional

ANALYSIS_BUCKETS = {
    "최근 추세": ("recent_10", "recent_20", "recent_30"),
    "로드 분석": ("bigroad", "big_eye", "small_road", "cockroach_road"),
    "패턴 분석": ("chop", "dragon", "ping_pong", "double_pattern"),
    "기억 패턴": ("pattern_memory",),
    "위험 분석": ("chop", "ping_pong"),
}


def _bucket_score(
    breakdown: Dict[str, Dict[str, Any]],
    keys: tuple,
    prediction: Optional[str],
) -> float:
    p_sum = b_sum = 0.0
    for key in keys:
        sig = breakdown.get(key) or {}
        p_sum += float(sig.get("weighted_p") or sig.get("raw_p") or 0)
        b_sum += float(sig.get("weighted_b") or sig.get("raw_b") or 0)
    total = p_sum + b_sum
    if total <= 0:
        return 0.0
    if prediction == "P":
        return round(p_sum / total * 100, 1)
    if prediction == "B":
        return round(b_sum / total * 100, 1)
    return round(max(p_sum, b_sum) / total * 100, 1)


def build_top_analysis_reasons(
    ai_result: Dict[str, Any],
    limit: int = 5,
) -> List[Dict[str, Any]]:
    prediction = ai_result.get("prediction")
    breakdown = ai_result.get("signal_breakdown") or {}
    risk_level = ai_result.get("risk_level", "LOW")
    low_conf = ai_result.get("low_confidence", False)

    rows: List[Dict[str, Any]] = []
    for label, keys in ANALYSIS_BUCKETS.items():
        score = _bucket_score(breakdown, keys, prediction)
        if label == "위험 분석":
            risk_map = {"LOW": 85, "MEDIUM": 65, "HIGH": 40, "EXTREME": 25}
            score = risk_map.get(str(risk_level).upper(), 50)
            if low_conf:
                score = min(score, 45)
        rows.append({"label": label, "score": score})

    rows.sort(key=lambda x: x["score"], reverse=True)
    return rows[:limit]
