"""
Pattern Similarity Engine — CASINO PRO AI v4.

Analysis/record-keeping only. Not betting advice.
"""

from typing import Any, Dict, List, Optional

PATTERN_LENGTHS = (6, 8, 10, 12, 16, 20)
EXACT_MIN_TOTAL = 5
SIMILAR_MIN_TOTAL = 10
SIMILARITY_THRESHOLD = 0.75
INFLUENCE_THRESHOLD = 0.80


def _pb_only(history: List[str]) -> List[str]:
    return [x for x in history if x in ("P", "B")]


def hamming_similarity(a: str, b: str) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    matches = sum(1 for x, y in zip(a, b) if x == y)
    return matches / len(a)


def _empty_result(reason=None):
    reasons = reason or ["패턴 표본 부족"]
    return {
        "prediction": None,
        "p_probability": 0.5,
        "b_probability": 0.5,
        "confidence": 0.0,
        "matched_patterns": [],
        "sample_size": 0,
        "reason": reasons,
    }


def _detect_shape_tags(pb: List[str]) -> List[str]:
    tags = []
    if len(pb) >= 4 and all(pb[i] != pb[i + 1] for i in range(min(6, len(pb) - 1))):
        tags.append("alternating")
    if len(pb) >= 4 and pb[-1] == pb[-2] == pb[-3]:
        tags.append("dragon")
    if len(pb) >= 6:
        seg = pb[-6:]
        if seg == seg[::-1]:
            tags.append("mirror")
    if len(pb) >= 4 and pb[-2] == pb[-1] and pb[-4] == pb[-3]:
        tags.append("ping_pong")
    if len(pb) >= 4 and all(pb[i] != pb[i + 1] for i in range(len(pb[-4:]) - 1)):
        tags.append("chop")
    return tags


def analyze_pattern_similarity(history, db) -> Dict[str, Any]:
    pb = _pb_only(history)
    if len(pb) < min(PATTERN_LENGTHS):
        result = _empty_result()
        result["similarity_percent"] = 0.0
        result["shape_tags"] = []
        return result

    matched_patterns: List[Dict[str, Any]] = []
    weighted_p = 0.0
    weighted_b = 0.0
    total_weight = 0.0
    sample_size = 0
    reasons: List[str] = []
    max_similarity = 0.0

    for length in PATTERN_LENGTHS:
        if len(pb) < length:
            continue

        current = "".join(pb[-length:])
        exact_row = db.lookup_pattern_memory(current)
        used_exact = False

        if exact_row and exact_row["total"] >= EXACT_MIN_TOTAL:
            row = exact_row
            sim = 1.0
            max_similarity = max(max_similarity, 1.0)
            match_type = "exact"
            used_exact = True
            min_total = EXACT_MIN_TOTAL
        else:
            row = None
            sim = 0.0
            match_type = "similar"
            best_sim = 0.0
            for candidate in db.get_pattern_memory_by_length(length):
                if candidate["pattern_key"] == current:
                    continue
                if candidate["total"] < SIMILAR_MIN_TOTAL:
                    continue
                s = hamming_similarity(current, candidate["pattern_key"])
                max_similarity = max(max_similarity, s)
                if s >= SIMILARITY_THRESHOLD and s > best_sim:
                    best_sim = s
                    row = candidate
                    sim = s

            if row is None:
                continue
            min_total = SIMILAR_MIN_TOTAL

        if sim < INFLUENCE_THRESHOLD and match_type != "exact":
            continue

        max_similarity = max(max_similarity, sim)

        total = row["total"]
        p_rate = row["p_rate"]
        b_rate = row["b_rate"]
        weight = total * sim
        weighted_p += p_rate * weight
        weighted_b += b_rate * weight
        total_weight += weight
        sample_size += total

        side = "PLAYER" if p_rate >= b_rate else "BANKER"
        prefix = "동일 패턴" if match_type == "exact" else "유사 패턴"
        reasons.append(f"{prefix} 과거 {total}회 중 {side} 우세")

        matched_patterns.append({
            "pattern_key": row["pattern_key"],
            "length": length,
            "match_type": match_type,
            "similarity": round(sim, 4),
            "total": total,
            "p_rate": p_rate,
            "b_rate": b_rate,
        })

    if total_weight <= 0:
        result = _empty_result()
        result["similarity_percent"] = round(max_similarity * 100.0, 2)
        result["shape_tags"] = _detect_shape_tags(pb)
        return result

    p_prob = round(weighted_p / total_weight, 4)
    b_prob = round(weighted_b / total_weight, 4)
    norm = p_prob + b_prob
    if norm > 0:
        p_prob = round(p_prob / norm, 4)
        b_prob = round(b_prob / norm, 4)

    prediction = "P" if p_prob >= b_prob else "B"
    margin = abs(p_prob - b_prob)
    confidence = round(min(0.50 + margin + sample_size * 0.001, 0.75), 4)

    return {
        "prediction": prediction,
        "p_probability": p_prob,
        "b_probability": b_prob,
        "confidence": confidence,
        "matched_patterns": matched_patterns,
        "sample_size": sample_size,
        "reason": reasons,
        "similarity_percent": round(max(max_similarity, margin) * 100.0, 2),
        "shape_tags": _detect_shape_tags(pb),
    }
