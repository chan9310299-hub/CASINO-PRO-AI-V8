"""Losing streak tracking — CASINO PRO AI v6."""

from typing import Any, Dict, List


def compute_losing_streaks(resolved_rows: List[dict]) -> Dict[str, Any]:
    """From resolved predictions (P/B actual, excluding PASS and ties)."""
    outcomes = []
    for row in resolved_rows:
        pred = row.get("prediction")
        if pred not in ("P", "B"):
            continue
        if row.get("is_correct") == 1:
            outcomes.append("W")
        elif row.get("is_correct") == 0:
            outcomes.append("L")

    current = 0
    for o in reversed(outcomes):
        if o == "L":
            current += 1
        else:
            break

    streaks: List[int] = []
    run = 0
    for o in outcomes:
        if o == "L":
            run += 1
        else:
            if run:
                streaks.append(run)
            run = 0
    if run:
        streaks.append(run)

    max_streak = max(streaks) if streaks else 0
    avg_streak = round(sum(streaks) / len(streaks), 2) if streaks else 0.0

    last_20 = outcomes[-20:]
    last_50 = outcomes[-50:]
    last_20_losses = sum(1 for o in last_20 if o == "L")
    last_50_losses = sum(1 for o in last_50 if o == "L")

    return {
        "current_losing_streak": current,
        "average_losing_streak": avg_streak,
        "maximum_losing_streak": max_streak,
        "last_20_losses": last_20_losses,
        "last_50_losses": last_50_losses,
        "last_20_total": len(last_20),
        "last_50_total": len(last_50),
    }


def min_confidence_for_streak(current_streak: int) -> float:
    if current_streak >= 5:
        return 0.98
    if current_streak >= 4:
        return 0.95
    if current_streak >= 3:
        return 0.90
    if current_streak >= 2:
        return 0.75
    return 0.50
