"""Road Agreement score — CASINO PRO AI v6."""

from typing import Any, Dict, List, Optional


def _side_from_breakdown(entry: Dict[str, Any]) -> Optional[str]:
    if not entry.get("active"):
        return None
    raw = entry.get("raw") or {}
    p, b = raw.get("P", 0), raw.get("B", 0)
    if p == b:
        return None
    return "P" if p > b else "B"


def compute_road_agreement(base_result: Dict[str, Any], voters: List[Dict[str, Any]]) -> float:
    sides: List[str] = []

    breakdown = base_result.get("signal_breakdown") or {}
    for name in ("bigroad", "big_eye", "small_road", "cockroach_road", "pattern_memory"):
        side = _side_from_breakdown(breakdown.get(name, {}))
        if side:
            sides.append(side)

    for name in ("recent_10", "recent_20", "recent_30"):
        side = _side_from_breakdown(breakdown.get(name, {}))
        if side:
            sides.append(side)

    for voter in voters:
        vote = voter.get("vote")
        if vote in ("P", "B"):
            sides.append(vote)

    if not sides:
        return 0.0

    p_count = sides.count("P")
    b_count = sides.count("B")
    majority = max(p_count, b_count)
    return round(majority / len(sides) * 100.0, 2)
