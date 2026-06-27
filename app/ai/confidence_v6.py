"""Dynamic confidence — CASINO PRO AI v6."""

from typing import Any, Dict, List

MIN_CONFIDENCE = 0.50
MAX_CONFIDENCE = 0.99


def compute_dynamic_confidence(
    raw_confidence: float,
    sample_size: int,
    road_agreement_pct: float,
    pattern_similarity_pct: float,
    signal_agreement: float,
    trend_consistency: float,
    recent_accuracy_pct: float,
    voter_agreement_pct: float,
) -> float:
    base = raw_confidence

    sample_boost = min(sample_size / 500.0, 0.08)
    road_boost = (road_agreement_pct / 100.0) * 0.06
    pattern_boost = (pattern_similarity_pct / 100.0) * 0.06
    signal_boost = signal_agreement * 0.05
    trend_boost = trend_consistency * 0.04
    acc_boost = (recent_accuracy_pct / 100.0) * 0.05
    voter_boost = (voter_agreement_pct / 100.0) * 0.04

    conf = base + sample_boost + road_boost + pattern_boost
    conf += signal_boost + trend_boost + acc_boost + voter_boost

    max_cap = MAX_CONFIDENCE
    if not (
        sample_size > 5000
        and recent_accuracy_pct > 80.0
        and voter_agreement_pct > 95.0
    ):
        max_cap = min(max_cap, 0.78)

    if sample_size < 30:
        max_cap = min(max_cap, 0.62)
    elif sample_size < 100:
        max_cap = min(max_cap, 0.70)

    if recent_accuracy_pct < 55.0:
        max_cap = min(max_cap, 0.60)

    return round(max(MIN_CONFIDENCE, min(conf, max_cap)), 4)


def voter_agreement_pct(voters: List[Dict[str, Any]]) -> float:
    votes = [v["vote"] for v in voters if v.get("vote") in ("P", "B")]
    if not votes:
        return 0.0
    majority = max(votes.count("P"), votes.count("B"))
    return round(majority / len(votes) * 100.0, 2)
