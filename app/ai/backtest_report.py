"""Backtest report for UI — windows 100/300/500/1000."""

import json
from typing import Any, Dict, List, Tuple

from ai.backtest_engine import backtest_window

UI_BACKTEST_WINDOWS = (100, 300, 500, 1000)


def _signal_stats(rows: List[dict]) -> Dict[str, Dict[str, int]]:
    stats: Dict[str, Dict[str, int]] = {}
    for row in rows:
        if row.get("prediction") not in ("P", "B"):
            continue
        if row.get("is_correct") not in (0, 1):
            continue
        try:
            breakdown = json.loads(row.get("signal_breakdown_json") or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(breakdown, dict):
            continue
        pred = row["prediction"]
        for name, info in breakdown.items():
            if not isinstance(info, dict):
                continue
            vote = info.get("vote") or info.get("prediction")
            if vote not in ("P", "B"):
                continue
            bucket = stats.setdefault(name, {"correct": 0, "wrong": 0})
            if vote == pred:
                if row["is_correct"] == 1:
                    bucket["correct"] += 1
                else:
                    bucket["wrong"] += 1
    return stats


def best_worst_signals(rows: List[dict]) -> Tuple[str, str]:
    stats = _signal_stats(rows)
    if not stats:
        return "—", "—"
    ranked = []
    for name, s in stats.items():
        total = s["correct"] + s["wrong"]
        if total == 0:
            continue
        ranked.append((name, s["correct"] / total, total))
    if not ranked:
        return "—", "—"
    ranked.sort(key=lambda x: (x[1], x[2]), reverse=True)
    best = f"{ranked[0][0]} ({ranked[0][1]:.0%})"
    worst = f"{ranked[-1][0]} ({ranked[-1][1]:.0%})"
    return best, worst


def run_backtest_report(db) -> Dict[str, Any]:
    resolved = db.get_resolved_predictions_pb()
    results = {}
    for window in UI_BACKTEST_WINDOWS:
        subset = resolved[-window:] if len(resolved) >= window else resolved
        bt = backtest_window(resolved, window)
        best, worst = best_worst_signals(subset)
        db.save_backtest_report(window, bt, best, worst)
        results[str(window)] = {**bt, "best_signal": best, "worst_signal": worst}
    return results
