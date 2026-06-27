"""
Learning AI v3 — adaptive signal weights and pattern memory.

Analysis/record-keeping only. Not betting advice.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

WEIGHT_MIN = 0.2
WEIGHT_MAX = 5.0
WEIGHT_INCREASE = 0.03
WEIGHT_DECREASE = 0.03
MIN_SAMPLES_FOR_ADJUST = 30
HIGH_ACCURACY = 0.70
LOW_ACCURACY = 0.55
PATTERN_LENGTHS = (6, 8, 10, 12, 16, 20)
PATTERN_MIN_TOTAL = 5

LEARNING_SIGNAL_DEFAULTS: Dict[str, float] = {
    "recent_10": 0.45,
    "recent_20": 0.55,
    "recent_30": 0.65,
    "bigroad": 2.0,
    "dragon": 2.5,
    "chop": 1.75,
    "ping_pong": 1.25,
    "double_pattern": 1.25,
    "big_eye": 1.2,
    "small_road": 1.2,
    "cockroach_road": 1.2,
    "pattern_memory": 1.0,
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

SIGNAL_ALIASES = {
    "big_road_trend": "bigroad",
}


def normalize_signal_name(name: str) -> str:
    return SIGNAL_ALIASES.get(name, name)


def clamp_weight(value: float) -> float:
    return max(WEIGHT_MIN, min(WEIGHT_MAX, round(value, 4)))


def adjust_weight_from_accuracy(current: float, accuracy: float, total: int) -> float:
    if total < MIN_SAMPLES_FOR_ADJUST:
        return current
    if accuracy >= HIGH_ACCURACY:
        return clamp_weight(current + WEIGHT_INCREASE)
    if accuracy <= LOW_ACCURACY:
        return clamp_weight(current - WEIGHT_DECREASE)
    return current


def make_pattern_key(pb: List[str], length: int) -> Optional[str]:
    if len(pb) < length:
        return None
    segment = pb[-length:]
    if not all(x in ("P", "B") for x in segment):
        return None
    return "".join(segment)


def lookup_pattern_memory(db, pb: List[str]) -> Dict[str, Any]:
    """Return aggregated pattern-memory bias for current pb sequence."""
    best = None
    for length in PATTERN_LENGTHS:
        key = make_pattern_key(pb, length)
        if not key:
            continue
        row = db.lookup_pattern_memory(key)
        if not row or row["total"] < PATTERN_MIN_TOTAL:
            continue
        if best is None or row["total"] > best["total"]:
            best = {**row, "length": length}

    if best is None:
        return {"active": False}

    total = best["total"]
    p_rate = best["p_rate"]
    b_rate = best["b_rate"]
    strength = min(0.5 + total * 0.02, 1.5)

    if p_rate >= b_rate:
        raw_p, raw_b = strength * p_rate, strength * (1 - p_rate) * 0.5
        reason = f"유사 패턴 과거 {total}회 중 PLAYER 우세"
    else:
        raw_p, raw_b = strength * (1 - b_rate) * 0.5, strength * b_rate
        reason = f"유사 패턴 과거 {total}회 중 BANKER 우세"

    return {
        "active": True,
        "raw_p": raw_p,
        "raw_b": raw_b,
        "reason": reason,
        "total": total,
        "pattern_length": best["length"],
        "pattern_key": best["pattern_key"],
    }


def record_pattern_after_hand(db, pb: List[str]) -> None:
    """Update pattern memory after a new P/B result (ties excluded from pb)."""
    if len(pb) < 2:
        return

    next_result = pb[-1]
    if next_result not in ("P", "B"):
        return

    for length in PATTERN_LENGTHS:
        if len(pb) < length + 1:
            continue
        pattern_key = "".join(pb[-(length + 1):-1])
        db.upsert_pattern_memory(pattern_key, length, next_result)


def update_weights_after_resolution(db, pending_row: dict, was_correct: bool) -> None:
    import json

    breakdown_raw = pending_row.get("signal_breakdown_json", "{}")
    if isinstance(breakdown_raw, str):
        breakdown = json.loads(breakdown_raw)
    else:
        breakdown = breakdown_raw or {}

    for raw_name, entry in breakdown.items():
        if not entry.get("active"):
            continue
        signal_name = normalize_signal_name(raw_name)
        if signal_name not in LEARNING_SIGNAL_DEFAULTS:
            continue
        db.update_signal_performance(signal_name, was_correct)


def build_adaptive_weight_map(db) -> Dict[str, float]:
    """Weights for PredictionEngine (includes base_p/base_b)."""
    learned = db.get_all_signal_weights()
    weights = {
        "base_p": 1.0,
        "base_b": 1.0,
    }
    for name, default in LEARNING_SIGNAL_DEFAULTS.items():
        weights[name] = learned.get(name, default)
    return weights


def get_adaptive_meta(db, ai_result: Optional[dict] = None) -> Dict[str, Any]:
    rows = []
    for name in LEARNING_SIGNAL_DEFAULTS:
        row = db.get_signal_weight(name)
        if row:
            rows.append(row)
    patterns = db.get_pattern_memory_count()

    best = None
    worst = None
    for row in rows:
        if row["total"] < 5:
            continue
        if best is None or row["accuracy"] > best["accuracy"]:
            best = row
        if worst is None or row["accuracy"] < worst["accuracy"]:
            worst = row

    pattern_reason = "—"
    if ai_result:
        for r in ai_result.get("reason_in_korean") or ai_result.get("reason") or []:
            if "유사 패턴" in r:
                pattern_reason = r
                break

    return {
        "signal_count": len(rows),
        "best_signal": best["signal_name"] if best else "—",
        "best_accuracy": best["accuracy"] if best else 0.0,
        "worst_signal": worst["signal_name"] if worst else "—",
        "worst_accuracy": worst["accuracy"] if worst else 0.0,
        "pattern_memory_count": patterns,
        "pattern_reason": pattern_reason,
    }
