"""Performance dashboard metrics."""

from typing import Any, Dict, List, Optional

from ai.losing_streak import compute_losing_streaks


def health_color(resolved: int, accuracy: float, risk_level: str) -> str:
    if resolved < 10:
        return "gray"
    if risk_level in ("HIGH", "EXTREME"):
        return "red"
    if accuracy >= 55 and resolved >= 30:
        return "green"
    if resolved >= 10:
        return "yellow"
    return "gray"


def build_performance_dashboard(db, history: List[str], ai_result: Optional[dict] = None) -> Dict[str, Any]:
    learning = db.get_learning_stats()
    resolved = db.get_resolved_predictions_pb()
    streaks = compute_losing_streaks(resolved)
    confidences = [
        float(r["confidence"]) for r in resolved
        if r.get("prediction") in ("P", "B") and r.get("confidence") is not None
    ]
    avg_conf = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
    pass_rate = db.get_v6_pass_rate() if hasattr(db, "get_v6_pass_rate") else 0.0
    risk = (ai_result or {}).get("risk_level", "LOW")

    return {
        "total_input_hands": len(history),
        "total_ai_predictions": learning["total_predictions"],
        "resolved_predictions": learning["total_resolved"],
        "overall_accuracy": learning["overall_accuracy"],
        "recent_30_accuracy": learning["recent_30_accuracy"],
        "recent_100_accuracy": learning["recent_100_accuracy"],
        "current_losing_streak": streaks["current_losing_streak"],
        "max_losing_streak": streaks["maximum_losing_streak"],
        "pass_rate": pass_rate,
        "avg_confidence": avg_conf,
        "pattern_memory_count": db.get_pattern_memory_count(),
        "signal_count": len(db.get_all_signal_weights()),
        "health_color": health_color(learning["total_resolved"], learning["overall_accuracy"], risk),
    }
