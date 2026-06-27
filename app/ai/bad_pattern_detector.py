"""Bad Pattern Detector — CASINO PRO AI v6."""

from typing import Any, Dict, List


def _is_chop(seq: List[str]) -> bool:
    if len(seq) < 4:
        return False
    return all(seq[i] != seq[i + 1] for i in range(len(seq) - 1))


def detect_bad_patterns(pb: List[str], base_result: Dict[str, Any]) -> Dict[str, Any]:
    reasons: List[str] = []
    detected = False

    if len(pb) >= 8 and _is_chop(pb[-8:]):
        detected = True
        reasons.append("교대 혼조 — alternating chaos")

    ws = base_result.get("weighted_score") or {"P": 0, "B": 0}
    total = ws["P"] + ws["B"]
    if total > 0:
        margin = abs(ws["P"] - ws["B"]) / total
        if margin < 0.05:
            detected = True
            reasons.append("mixed signals — 신호 혼재")

    status = base_result.get("status", "")
    if "혼조" in status:
        detected = True
        reasons.append("unstable road — 불안정 로드")

    if len(pb) >= 5:
        last = pb[-1]
        streak = 1
        for i in range(len(pb) - 2, -1, -1):
            if pb[i] == last:
                streak += 1
            else:
                break
        if streak >= 4 and len(pb) >= 8:
            prior = pb[-(streak + 2):-streak]
            if prior and all(x != last for x in prior[-2:]):
                detected = True
                reasons.append("false dragon — 드래곤 신뢰도 낮음")

    breakdown = base_result.get("signal_breakdown") or {}
    active = sum(1 for v in breakdown.values() if v.get("active"))
    if active >= 6:
        sides = []
        for entry in breakdown.values():
            if not entry.get("active"):
                continue
            raw = entry.get("raw") or {}
            if raw.get("P", 0) > raw.get("B", 0):
                sides.append("P")
            elif raw.get("B", 0) > raw.get("P", 0):
                sides.append("B")
        if sides and min(sides.count("P"), sides.count("B")) >= 2:
            detected = True
            reasons.append("pattern collapse — 패턴 붕괴")

    return {
        "detected": detected,
        "recommend_pass": detected,
        "reasons": reasons,
    }
