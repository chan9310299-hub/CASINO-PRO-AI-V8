"""Self Optimizer — CASINO PRO AI v6. Runs every 100 resolved predictions."""

import json
from typing import Any, Dict, List

from ai.adaptive_learning import LEARNING_SIGNAL_DEFAULTS, clamp_weight
from ai.backtest_engine import backtest_window

OPTIMIZE_EVERY = 100
WEIGHT_STEPS = (-0.1, 0.0, 0.1)


def should_run_optimizer(resolved_count: int, last_run_at: int) -> bool:
    if resolved_count < OPTIMIZE_EVERY:
        return False
    return resolved_count - last_run_at >= OPTIMIZE_EVERY


def optimize_weights(db, resolved_rows: List[dict]) -> Dict[str, Any]:
    baseline = backtest_window(resolved_rows, min(300, len(resolved_rows)))
    accuracy_before = baseline["accuracy"]

    old_weights = db.get_all_signal_weights()
    best_weights = dict(old_weights)
    best_accuracy = accuracy_before

    for signal in LEARNING_SIGNAL_DEFAULTS:
        row = db.get_signal_weight(signal)
        if not row:
            continue
        current = row["weight"]
        for step in WEIGHT_STEPS:
            trial = clamp_weight(current + step)
            db.update_signal_weight(signal, trial)
        db.update_signal_weight(signal, current)

    for signal in LEARNING_SIGNAL_DEFAULTS:
        row = db.get_signal_weight(signal)
        if not row:
            continue
        current = row["weight"]
        for step in WEIGHT_STEPS:
            trial = clamp_weight(current + step)
            if trial == current:
                continue
            db.update_signal_weight(signal, trial)
            trial_acc = accuracy_before
            if trial_acc >= best_accuracy:
                best_accuracy = trial_acc
                best_weights[signal] = trial
            db.update_signal_weight(signal, current)

    for signal, weight in best_weights.items():
        db.update_signal_weight(signal, weight)

    accuracy_after = best_accuracy
    return {
        "old_weights": old_weights,
        "new_weights": best_weights,
        "accuracy_before": accuracy_before,
        "accuracy_after": accuracy_after,
    }
