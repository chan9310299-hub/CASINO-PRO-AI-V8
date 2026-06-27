"""Pattern ranking — top patterns by occurrences."""

from datetime import datetime
from typing import Any, Dict, List


def rank_patterns(db, limit: int = 20) -> List[Dict[str, Any]]:
    db.ensure_v6_tables()
    db.refresh_pattern_rank_cache()
    rows = db.get_pattern_rank_top(limit)
    if not rows:
        return []
    result = []
    for row in rows:
        total = row.get("occurrences") or row.get("total") or 0
        p_rate = row.get("p_rate") or 0.0
        b_rate = row.get("b_rate") or 0.0
        conf = round(max(p_rate, b_rate) * min(1.0, total / 20.0), 4)
        result.append({
            "pattern": row.get("pattern_key", ""),
            "occurrences": total,
            "next_p_pct": round(p_rate * 100, 1),
            "next_b_pct": round(b_rate * 100, 1),
            "confidence": conf,
            "last_seen": row.get("last_seen") or row.get("updated_at") or "—",
        })
    return result


def has_enough_pattern_data(db, min_patterns: int = 5) -> bool:
    return db.get_pattern_memory_count() >= min_patterns
