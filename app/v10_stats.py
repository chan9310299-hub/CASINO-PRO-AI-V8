"""Home-screen statistics — CASINO PRO AI v10."""

from datetime import date
from typing import Any, Dict


def _today_accuracy(db) -> float:
    try:
        rows = db.get_resolved_predictions_pb() or []
    except Exception:
        return 0.0
    today = date.today().isoformat()
    today_rows = [
        r for r in rows
        if str(r.get("created_at", "")).startswith(today)
    ]
    if not today_rows:
        return 0.0
    correct = sum(1 for r in today_rows if r.get("is_correct") == 1)
    return round(correct / len(today_rows) * 100, 1)


def build_v10_home_stats(db, learning: Dict[str, Any], streak_stats: Dict[str, Any]) -> Dict[str, Any]:
    learning = learning or {}
    streak_stats = streak_stats or {}
    return {
        "today_accuracy": _today_accuracy(db),
        "recent_30_accuracy": learning.get("recent_30_accuracy", 0),
        "recent_100_accuracy": learning.get("recent_100_accuracy", 0),
        "current_win": streak_stats.get("current_win", 0),
        "current_lose": streak_stats.get("current_lose", 0),
        "max_win": streak_stats.get("max_win", 0),
        "max_lose": streak_stats.get("max_lose", 0),
        "total_predictions": learning.get("total_predictions", 0),
        "total_hits": learning.get("correct", 0),
    }
