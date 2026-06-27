"""CASINO PRO AI v9 — expanded pattern analysis signals."""

from typing import Any, Dict, List, Optional

SignalResult = Dict[str, Any]

V9_SIGNAL_NAMES = (
    "streak_ai",
    "chop_ai",
    "dragon_ai",
    "reversal_ai",
    "two_side_balance_ai",
    "road_consensus_ai",
    "memory_similarity_ai",
    "risk_filter_ai",
    "meta_vote_ai",
    "anti_six_loss_ai",
)

DEFAULT_V9_WEIGHTS = {
    "streak_ai": 1.2,
    "chop_ai": 1.3,
    "dragon_ai": 1.5,
    "reversal_ai": 1.1,
    "two_side_balance_ai": 1.0,
    "road_consensus_ai": 1.4,
    "memory_similarity_ai": 1.3,
    "risk_filter_ai": 1.2,
    "meta_vote_ai": 2.0,
    "anti_six_loss_ai": 1.8,
}


def _result(name: str, prediction: str, confidence: float, reason: str, risk_level: str) -> SignalResult:
    return {
        "name": name,
        "prediction": prediction if prediction in ("P", "B", "PASS") else "PASS",
        "confidence": round(max(0.0, min(0.99, confidence)), 4),
        "reason": reason,
        "risk_level": risk_level if risk_level in ("LOW", "MEDIUM", "HIGH", "EXTREME") else "LOW",
    }


def streak_ai(pb: List[str], current_streak: int = 0) -> SignalResult:
    if len(pb) < 4:
        return _result("streak_ai", "PASS", 0.0, "연속 패턴 데이터 부족", "MEDIUM")
    last = pb[-1]
    streak = 1
    for i in range(len(pb) - 2, -1, -1):
        if pb[i] == last:
            streak += 1
        else:
            break
    if streak >= 4:
        conf = min(0.85, 0.55 + streak * 0.08)
        return _result(
            "streak_ai", last, conf,
            f"연속 {streak}회 {last} — 추세 신호", "MEDIUM" if streak < 6 else "HIGH",
        )
    return _result("streak_ai", "PASS", 0.4, "연속 길이 짧음 — 관망", "LOW")


def chop_ai(pb: List[str]) -> SignalResult:
    if len(pb) < 6:
        return _result("chop_ai", "PASS", 0.0, "교차 패턴 데이터 부족", "MEDIUM")
    recent = pb[-6:]
    changes = sum(1 for i in range(len(recent) - 1) if recent[i] != recent[i + 1])
    if changes >= 4:
        nxt = "B" if recent[-1] == "P" else "P"
        return _result("chop_ai", nxt, 0.62, "교차(chop) 패턴 — 다음 반전 통계", "LOW")
    return _result("chop_ai", "PASS", 0.35, "교차 패턴 약함", "LOW")


def dragon_ai(pb: List[str]) -> SignalResult:
    if len(pb) < 5:
        return _result("dragon_ai", "PASS", 0.0, "드래곤 데이터 부족", "MEDIUM")
    last = pb[-1]
    streak = 1
    for i in range(len(pb) - 2, -1, -1):
        if pb[i] == last:
            streak += 1
        else:
            break
    if streak >= 3:
        return _result(
            "dragon_ai", last, min(0.78, 0.5 + streak * 0.1),
            f"드래곤 {streak} — 같은 방향 통계", "MEDIUM",
        )
    return _result("dragon_ai", "PASS", 0.3, "드래곤 미형성", "LOW")


def reversal_ai(pb: List[str]) -> SignalResult:
    if len(pb) < 8:
        return _result("reversal_ai", "PASS", 0.0, "반전 분석 데이터 부족", "MEDIUM")
    last = pb[-1]
    streak = 1
    for i in range(len(pb) - 2, -1, -1):
        if pb[i] == last:
            streak += 1
        else:
            break
    if streak >= 5:
        rev = "B" if last == "P" else "P"
        return _result(
            "reversal_ai", rev, 0.58,
            f"장기 연속 {streak} 후 반전 통계", "HIGH",
        )
    return _result("reversal_ai", "PASS", 0.35, "반전 조건 미충족", "LOW")


def two_side_balance_ai(pb: List[str]) -> SignalResult:
    if len(pb) < 10:
        return _result("two_side_balance_ai", "PASS", 0.0, "균형 분석 데이터 부족", "MEDIUM")
    p = pb[-20:].count("P")
    b = pb[-20:].count("B")
    total = p + b
    if total == 0:
        return _result("two_side_balance_ai", "PASS", 0.0, "표본 없음", "LOW")
    p_rate = p / total
    if p_rate >= 0.65:
        return _result("two_side_balance_ai", "B", 0.6, f"P 과다({p_rate:.0%}) — B 쪽 균형", "LOW")
    if p_rate <= 0.35:
        return _result("two_side_balance_ai", "P", 0.6, f"B 과다 — P 쪽 균형", "LOW")
    return _result("two_side_balance_ai", "PASS", 0.4, "양측 균형 — 관망", "LOW")


def road_consensus_ai(base_result: Dict[str, Any]) -> SignalResult:
    ws = base_result.get("weighted_score") or {"P": 0, "B": 0}
    p, b = ws.get("P", 0), ws.get("B", 0)
    total = p + b
    if total <= 0:
        return _result("road_consensus_ai", "PASS", 0.0, "로드 합의 없음", "MEDIUM")
    margin = abs(p - b) / total
    if margin < 0.08:
        return _result("road_consensus_ai", "PASS", margin, "로드 합의 약함", "MEDIUM")
    vote = "P" if p >= b else "B"
    return _result(
        "road_consensus_ai", vote, min(0.85, 0.5 + margin),
        f"로드 합의 {vote} (마진 {margin:.0%})", "LOW",
    )


def memory_similarity_ai(pattern_sim: Dict[str, Any]) -> SignalResult:
    sim = pattern_sim.get("similarity_percent", 0.0)
    sample = pattern_sim.get("sample_size", 0)
    if sample < 3 or sim < 50:
        return _result("memory_similarity_ai", "PASS", 0.0, "패턴 메모리 표본 부족", "MEDIUM")
    p_prob = pattern_sim.get("p_probability", 0.5)
    b_prob = pattern_sim.get("b_probability", 0.5)
    vote = "P" if p_prob >= b_prob else "B"
    conf = min(0.88, sim / 100.0 * 0.9)
    return _result(
        "memory_similarity_ai", vote, conf,
        f"유사 패턴 {sim:.0f}% — {vote} 통계", "LOW" if sim >= 70 else "MEDIUM",
    )


def risk_filter_ai(risk_level: str, confidence: float) -> SignalResult:
    if risk_level in ("HIGH", "EXTREME"):
        return _result("risk_filter_ai", "PASS", confidence, f"리스크 {risk_level} — PASS", risk_level)
    if confidence < 0.55:
        return _result("risk_filter_ai", "PASS", confidence, "신뢰도 낮음 — PASS", "MEDIUM")
    return _result("risk_filter_ai", "PASS", confidence, "리스크 필터 통과", "LOW")


def meta_vote_ai(voters: List[Dict[str, Any]]) -> SignalResult:
    p = b = 0.0
    for v in voters:
        vote = v.get("vote")
        if vote not in ("P", "B"):
            continue
        w = float(v.get("weight", 1.0)) * float(v.get("confidence", 0.5))
        if vote == "P":
            p += w
        else:
            b += w
    total = p + b
    if total <= 0:
        return _result("meta_vote_ai", "PASS", 0.0, "메타 투표 표본 없음", "MEDIUM")
    if abs(p - b) / total < 0.1:
        return _result("meta_vote_ai", "PASS", abs(p - b) / total, "메타 투표 혼조", "MEDIUM")
    vote = "P" if p >= b else "B"
    conf = max(p, b) / total
    return _result("meta_vote_ai", vote, conf, f"메타 투표 {vote} 우세", "LOW")


def anti_six_loss_ai(
    current_streak: int,
    protection_enabled: bool = True,
) -> SignalResult:
    if not protection_enabled:
        return _result("anti_six_loss_ai", "PASS", 0.5, "보호 모드 OFF", "LOW")
    if current_streak >= 4:
        return _result(
            "anti_six_loss_ai", "PASS", 0.95,
            f"연패 {current_streak} — 6단계 보호 PASS", "HIGH",
        )
    if current_streak >= 2:
        return _result(
            "anti_six_loss_ai", "PASS", 0.7,
            f"연패 {current_streak} — 보수적 관망", "MEDIUM",
        )
    return _result("anti_six_loss_ai", "PASS", 0.5, "연패 위험 낮음", "LOW")


def collect_v9_signals(
    history: List[str],
    base_result: Dict[str, Any],
    pattern_sim: Dict[str, Any],
    current_streak: int = 0,
    risk_level: str = "LOW",
    confidence: float = 0.5,
    voters: Optional[List[Dict[str, Any]]] = None,
    protection_enabled: bool = True,
) -> List[SignalResult]:
    pb = [x for x in history if x in ("P", "B")]
    signals = [
        streak_ai(pb, current_streak),
        chop_ai(pb),
        dragon_ai(pb),
        reversal_ai(pb),
        two_side_balance_ai(pb),
        road_consensus_ai(base_result),
        memory_similarity_ai(pattern_sim),
        risk_filter_ai(risk_level, confidence),
        meta_vote_ai(voters or []),
        anti_six_loss_ai(current_streak, protection_enabled),
    ]
    return signals


def signal_to_voter(signal: SignalResult) -> Dict[str, Any]:
    vote = signal.get("prediction")
    if vote == "PASS":
        vote = None
    return {
        "name": signal["name"],
        "vote": vote,
        "confidence": signal.get("confidence", 0.0),
        "weight": DEFAULT_V9_WEIGHTS.get(signal["name"], 1.0),
        "reason": signal.get("reason", ""),
        "risk_level": signal.get("risk_level", "LOW"),
    }
