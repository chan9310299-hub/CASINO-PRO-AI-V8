"""
Multi-AI Voting Engine — CASINO PRO AI v4.

Analysis/record-keeping only. Not betting advice.
"""

from collections import Counter
from typing import Any, Dict, List, Optional

MIN_CONFIDENCE = 0.50
MAX_CONFIDENCE_DEFAULT = 0.78


def calibrate_confidence(
    raw: float,
    sample_size: int,
    ai_accuracy_pct: float,
) -> float:
    max_conf = MAX_CONFIDENCE_DEFAULT
    if sample_size < 30:
        max_conf = min(max_conf, 0.62)
    elif sample_size < 100:
        max_conf = min(max_conf, 0.70)
    if ai_accuracy_pct < 55.0:
        max_conf = min(max_conf, 0.60)
    return round(max(MIN_CONFIDENCE, min(raw, max_conf)), 4)


def _vote_from_scores(p_score: float, b_score: float, threshold: float = 0.05):
    total = p_score + b_score
    if total <= 0:
        return None, 0.0, 0.5, 0.5
    p_prob = p_score / total
    b_prob = b_score / total
    if abs(p_prob - b_prob) < threshold:
        return None, abs(p_prob - b_prob), p_prob, b_prob
    vote = "P" if p_prob > b_prob else "B"
    conf = max(p_prob, b_prob)
    return vote, conf, p_prob, b_prob


def _trend_voter(pb: List[str]) -> Dict[str, Any]:
    if len(pb) < 10:
        return {
            "name": "trend_ai",
            "vote": None,
            "confidence": 0.0,
            "weight": 1.0,
            "reason": "최근 추세 데이터 부족",
        }

    counts = Counter(pb[-30:])
    total = counts["P"] + counts["B"]
    p_ratio = counts["P"] / total if total else 0.5
    vote = "P" if p_ratio >= 0.5 else "B"
    conf = max(p_ratio, 1 - p_ratio)
    side = "PLAYER" if vote == "P" else "BANKER"
    return {
        "name": "trend_ai",
        "vote": vote,
        "confidence": round(conf, 4),
        "weight": 1.2,
        "reason": f"최근 추세 {side} 우세 (P:{counts['P']} B:{counts['B']})",
    }


def _road_voter(base_result: Dict[str, Any]) -> Dict[str, Any]:
    ws = base_result.get("weighted_score") or {"P": 0, "B": 0}
    vote, conf, _, _ = _vote_from_scores(ws["P"], ws["B"])
    if vote is None:
        return {
            "name": "road_ai",
            "vote": None,
            "confidence": 0.0,
            "weight": 1.5,
            "reason": "로드 신호 혼조",
        }
    side = "PLAYER" if vote == "P" else "BANKER"
    return {
        "name": "road_ai",
        "vote": vote,
        "confidence": round(conf, 4),
        "weight": 1.5,
        "reason": f"BigRoad·파생로드 {side} 쪽",
    }


def _pattern_voter(pattern_sim: Dict[str, Any]) -> Dict[str, Any]:
    if not pattern_sim.get("matched_patterns"):
        return {
            "name": "pattern_ai",
            "vote": None,
            "confidence": 0.0,
            "weight": 1.3,
            "reason": "패턴 표본 부족",
        }
    vote = pattern_sim.get("prediction")
    conf = pattern_sim.get("confidence", 0.0)
    reason = pattern_sim["reason"][0] if pattern_sim.get("reason") else "패턴 유사도 분석"
    return {
        "name": "pattern_ai",
        "vote": vote,
        "confidence": conf,
        "weight": 1.3,
        "reason": reason,
    }


def _memory_voter(base_result: Dict[str, Any]) -> Dict[str, Any]:
    ws = base_result.get("weighted_score") or {"P": 0, "B": 0}
    learned = base_result.get("learned_weights") or {}
    p_score = ws["P"] * learned.get("dragon", 1.0)
    b_score = ws["B"] * learned.get("dragon", 1.0)
    vote, conf, _, _ = _vote_from_scores(p_score, b_score)
    if vote is None:
        return {
            "name": "memory_ai",
            "vote": None,
            "confidence": 0.0,
            "weight": 1.1,
            "reason": "학습 가중치 신호 약함",
        }
    side = "PLAYER" if vote == "P" else "BANKER"
    return {
        "name": "memory_ai",
        "vote": vote,
        "confidence": round(conf, 4),
        "weight": 1.1,
        "reason": f"적응형 학습 가중치 {side} 쪽",
    }


def _risk_voter(base_result: Dict[str, Any], pb: List[str]) -> Dict[str, Any]:
    status = base_result.get("status", "")
    ws = base_result.get("weighted_score") or {"P": 0, "B": 0}
    total = ws["P"] + ws["B"]
    margin = abs(ws["P"] - ws["B"]) / total if total else 0

    unstable = (
        "혼조" in status
        or "주의" in status
        or margin < 0.08
        or len(pb) < 12
    )
    if unstable:
        return {
            "name": "risk_ai",
            "vote": None,
            "confidence": 0.55,
            "weight": 0.8,
            "reason": "불안정 구간 — 신호 신중",
        }

    vote, conf, _, _ = _vote_from_scores(ws["P"], ws["B"])
    return {
        "name": "risk_ai",
        "vote": vote,
        "confidence": round(min(conf, 0.65), 4),
        "weight": 0.8,
        "reason": "리스크 구간 양호",
    }


def combine_votes(
    history: List[str],
    base_result: Dict[str, Any],
    pattern_similarity: Dict[str, Any],
    data_counts: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    pb = [x for x in history if x in ("P", "B")]
    data_counts = data_counts or {}

    voters = [
        _trend_voter(pb),
        _road_voter(base_result),
        _pattern_voter(pattern_similarity),
        _memory_voter(base_result),
        _risk_voter(base_result, pb),
    ]

    p_score = 0.0
    b_score = 0.0
    for voter in voters:
        if voter["vote"] is None:
            continue
        w = voter["weight"] * voter["confidence"]
        if voter["vote"] == "P":
            p_score += w
        else:
            b_score += w

    if p_score + b_score <= 0:
        ws = base_result.get("weighted_score") or {"P": 1.0, "B": 1.0}
        p_score = ws["P"]
        b_score = ws["B"]

    total = p_score + b_score
    probability_p = round(p_score / total, 4) if total else 0.5
    probability_b = round(b_score / total, 4) if total else 0.5
    prediction = "P" if probability_p >= probability_b else "B"

    raw_conf = max(probability_p, probability_b)
    sample_size = pattern_similarity.get("sample_size", 0) + len(pb)
    ai_accuracy = data_counts.get("ai_accuracy_pct", 0.0)
    confidence = calibrate_confidence(raw_conf, sample_size, ai_accuracy)

    return {
        "prediction": prediction,
        "confidence": confidence,
        "probability_p": probability_p,
        "probability_b": probability_b,
        "voters": voters,
        "weighted_p_score": round(p_score, 4),
        "weighted_b_score": round(b_score, 4),
    }
