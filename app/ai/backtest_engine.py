"""Backtest Engine — CASINO PRO AI v6."""

import json
from typing import Any, Dict, List, Optional

from ai.losing_streak import compute_losing_streaks

BACKTEST_WINDOWS = (100, 300, 500, 1000, 3000, 10000)


def _simulate_row(row: dict) -> Optional[str]:
    pred = row.get("prediction")
    if pred not in ("P", "B"):
        return "PASS"
    if row.get("is_correct") == 1:
        return "W"
    if row.get("is_correct") == 0:
        return "L"
    return None


def backtest_window(resolved_rows: List[dict], window: int) -> Dict[str, Any]:
    subset = resolved_rows[-window:] if len(resolved_rows) >= window else resolved_rows
    if not subset:
        return {
            "window": window,
            "accuracy": 0.0,
            "win_count": 0,
            "loss_count": 0,
            "draw_count": 0,
            "pass_count": 0,
            "pass_rate": 0.0,
            "avg_confidence": 0.0,
            "average_losing_streak": 0.0,
            "maximum_losing_streak": 0,
            "sample_size": 0,
        }

    wins = losses = passes = draws = 0
    confidences = []
    eval_rows = []

    for row in subset:
        pred = row.get("prediction")
        if pred == "PASS":
            passes += 1
            continue
        if pred not in ("P", "B"):
            continue
        confidences.append(float(row.get("confidence") or 0))
        if row.get("is_correct") == 1:
            wins += 1
            eval_rows.append({**row, "is_correct": 1})
        elif row.get("is_correct") == 0:
            losses += 1
            eval_rows.append({**row, "is_correct": 0})

    evaluated = wins + losses
    accuracy = round(wins / evaluated * 100.0, 2) if evaluated else 0.0
    streaks = compute_losing_streaks(eval_rows)
    total = len(subset)

    return {
        "window": window,
        "accuracy": accuracy,
        "win_count": wins,
        "loss_count": losses,
        "draw_count": draws,
        "pass_count": passes,
        "pass_rate": round(passes / total * 100.0, 2) if total else 0.0,
        "avg_confidence": round(sum(confidences) / len(confidences), 4) if confidences else 0.0,
        "average_losing_streak": streaks["average_losing_streak"],
        "maximum_losing_streak": streaks["maximum_losing_streak"],
        "sample_size": total,
    }


def run_all_backtests(resolved_rows: List[dict]) -> Dict[str, Any]:
    results = {}
    for window in BACKTEST_WINDOWS:
        results[str(window)] = backtest_window(resolved_rows, window)
    return results
