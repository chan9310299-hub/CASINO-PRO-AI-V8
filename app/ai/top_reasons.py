"""Top analysis reasons with scores — CASINO PRO AI v11."""

from typing import Any, Dict, List, Optional

from ai.similar_pattern_summary import build_similar_pattern_summary

ANALYSIS_BUCKETS = {
    "최근 흐름": ("recent_10", "recent_20", "recent_30"),
    "로드 분석": ("bigroad", "big_eye", "small_road", "cockroach_road"),
    "유사 패턴": ("pattern_memory",),
    "학습 가중치": ("dragon", "chop", "ping_pong", "double_pattern"),
    "위험도": (),
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


def _learning_weight_score(ai_result: Dict[str, Any], prediction: Optional[str]) -> float:
    meta = float(ai_result.get("meta_score") or 0)
    voters = ai_result.get("voters") or []
    p_w = b_w = 0.0
    for voter in voters:
        vote = voter.get("vote")
        if vote not in ("P", "B"):
            continue
        w = float(voter.get("weight") or 1.0) * float(voter.get("confidence") or 0.5)
        if vote == "P":
            p_w += w
        else:
            b_w += w
    total = p_w + b_w
    side_ratio = 0.5
    if total > 0 and prediction in ("P", "B"):
        side_ratio = (p_w if prediction == "P" else b_w) / total
    return round(min(99.0, max(meta, side_ratio) * 100), 1)


def _similar_pattern_score(ai_result: Dict[str, Any]) -> float:
    summary = ai_result.get("similar_pattern_summary")
    if summary:
        return float(summary.get("score") or 0)
    pattern_sim = ai_result.get("pattern_similarity") or {}
    return float(build_similar_pattern_summary(pattern_sim, ai_result.get("prediction")).get("score") or 0)


def build_top_analysis_reasons(
    ai_result: Dict[str, Any],
    limit: int = 5,
) -> List[Dict[str, Any]]:
    prediction = ai_result.get("prediction")
    breakdown = ai_result.get("signal_breakdown") or {}
    risk_level = ai_result.get("risk_level", "LOW")
    low_conf = ai_result.get("low_confidence", False)
    prot = ai_result.get("protection_mode") or {}

    rows: List[Dict[str, Any]] = []
    for label, keys in ANALYSIS_BUCKETS.items():
        if label == "유사 패턴":
            score = _similar_pattern_score(ai_result)
        elif label == "학습 가중치":
            score = _learning_weight_score(ai_result, prediction)
        elif label == "위험도":
            risk_map = {"LOW": 82, "MEDIUM": 62, "HIGH": 38, "EXTREME": 22}
            score = risk_map.get(str(risk_level).upper(), 50)
            streak = int(prot.get("current_streak") or 0)
            if streak >= 3:
                score = min(score, 35)
            if low_conf:
                score = min(score, 42)
        else:
            score = _bucket_score(breakdown, keys, prediction)
        rows.append({"label": label, "score": score})

    rows.sort(key=lambda x: x["score"], reverse=True)
    return rows[:limit]
