"""User-facing similar pattern summary — CASINO PRO AI v11."""

from typing import Any, Dict, Optional


def build_similar_pattern_summary(
    pattern_sim: Optional[Dict[str, Any]],
    prediction: Optional[str] = None,
) -> Dict[str, Any]:
    pattern_sim = pattern_sim or {}
    matched = pattern_sim.get("matched_patterns") or []
    count = len(matched)
    sample = int(pattern_sim.get("sample_size") or 0)
    p_prob = float(pattern_sim.get("p_probability") or 0.5)
    b_prob = float(pattern_sim.get("b_probability") or 0.5)
    sim_pct = float(pattern_sim.get("similarity_percent") or 0.0)

    if count == 0 and sample == 0:
        return {
            "similar_count": 0,
            "sample_size": 0,
            "favor": "—",
            "favor_side": None,
            "summary": "유사 패턴 데이터 없음",
            "score": 0.0,
        }

    favor_side = "P" if p_prob >= b_prob else "B"
    favor = "플레이어" if favor_side == "P" else "뱅커"
    align = prediction in (None, favor_side)
    score = round(min(99.0, sim_pct * 0.6 + (abs(p_prob - b_prob) * 100) * 0.4), 1)
    if not align and prediction in ("P", "B"):
        score = round(score * 0.75, 1)

    if count > 0:
        summary = f"유사 패턴 {count}건 · 과거 {sample}회 중 {favor} 우세"
    else:
        summary = f"패턴 표본 {sample}회 · {favor} 쪽 우세"

    return {
        "similar_count": count,
        "sample_size": sample,
        "favor": favor,
        "favor_side": favor_side,
        "summary": summary,
        "score": score,
    }
