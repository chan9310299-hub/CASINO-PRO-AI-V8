"""
AI prediction logging and learning statistics.

Record-keeping and analysis only — not betting advice.
"""

from typing import Any, Callable, Dict, Optional

from ai.adaptive_learning import (
    get_adaptive_meta,
    record_pattern_after_hand,
    update_weights_after_resolution,
)
from ai.self_optimizer import optimize_weights, should_run_optimizer


def compute_is_correct(prediction: str, actual_result: str) -> Optional[int]:
    if actual_result == "T":
        return None
    if actual_result not in ("P", "B"):
        return None
    if prediction == "PASS":
        return None
    return 1 if prediction == actual_result else 0


def calculate_learning_stats(db, ai_result: Optional[dict] = None) -> Dict[str, Any]:
    """Backward-compatible wrapper with adaptive learning meta."""
    stats = db.get_learning_stats()
    stats.update(get_adaptive_meta(db, ai_result))
    if ai_result and ai_result.get("v6_dashboard"):
        stats["v6_dashboard"] = ai_result["v6_dashboard"]
    return stats


def ensure_prediction_logged(db, history, ai_result) -> Optional[int]:
    prediction = ai_result.get("prediction")
    if prediction is None:
        return None

    hand_index = len(history) + 1
    if db.has_prediction_for_hand(hand_index):
        return None

    if db.get_unresolved_prediction() is not None:
        return None

    return db.insert_prediction_history(
        hand_index=hand_index,
        history_snapshot=list(history),
        prediction=prediction,
        confidence=ai_result.get("confidence", 0.0),
        weighted_score=ai_result.get("weighted_score")
        or ai_result.get("score", {"P": 0, "B": 0}),
        signal_breakdown_json=ai_result.get("signal_breakdown", {}),
        reason_json=ai_result.get("reason_in_korean")
        or ai_result.get("reason", []),
    )


def resolve_unresolved_prediction(db, actual_result: str) -> Optional[int]:
    pending = db.get_unresolved_prediction()
    if pending is None:
        return None

    is_correct = compute_is_correct(pending["prediction"], actual_result)
    updated = db.update_prediction_actual(
        pending["hand_index"],
        actual_result,
        is_correct,
    )
    if updated and is_correct is not None:
        update_weights_after_resolution(db, pending, is_correct == 1)

        resolved = db.get_resolved_predictions_pb()
        resolved_count = len(resolved)
        last_run = db.get_last_optimizer_resolved_count()
        if should_run_optimizer(resolved_count, last_run):
            result = optimize_weights(db, resolved)
            db.save_optimizer_v6(result, resolved_count)

    return pending["id"] if updated else None


def process_new_hand(db, actual_result: str, analyze_fn: Callable) -> Dict[str, Any]:
    resolve_unresolved_prediction(db, actual_result)
    db.add_result(actual_result)
    history = db.get_results()
    pb = [x for x in history if x in ("P", "B")]
    if actual_result in ("P", "B"):
        record_pattern_after_hand(db, pb)
    ai_result = analyze_fn(history)
    ensure_prediction_logged(db, history, ai_result)
    return ai_result
