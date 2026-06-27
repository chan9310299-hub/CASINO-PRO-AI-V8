"""Accumulated data count helpers for CASINO PRO AI v4."""

from typing import Any, Dict, List


def get_data_counts(db, history: List[str]) -> Dict[str, Any]:
    pb = [x for x in history if x in ("P", "B")]
    learning = db.get_learning_stats()
    weights = db.get_all_signal_weights()

    return {
        "total_input_hands": len(history),
        "accumulated_pb_hands": len(pb),
        "total_ai_predictions": learning["total_predictions"],
        "resolved_ai_predictions": learning["total_resolved"],
        "pattern_memory_count": db.get_pattern_memory_count(),
        "signal_count": len(weights),
        "ai_accuracy_pct": learning["overall_accuracy"],
    }
