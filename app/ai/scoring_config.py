"""
Central configuration for AI prediction signal weights.

All scoring weights live in this module. Pass a custom dict to
PredictionEngine(weights=...) or ScoringConfig(weights=...) to tune.
"""

from dataclasses import dataclass, field
from typing import Dict

from ai.adaptive_learning import LEARNING_SIGNAL_DEFAULTS


DEFAULT_SIGNAL_WEIGHTS: Dict[str, float] = {
    "base_p": 1.0,
    "base_b": 1.0,
    **LEARNING_SIGNAL_DEFAULTS,
}

SIGNAL_ALIASES = {
    "big_road_trend": "bigroad",
}


@dataclass
class ScoringConfig:
    """Single configuration object for all adjustable signal weights."""

    weights: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_SIGNAL_WEIGHTS))

    def __post_init__(self):
        merged = dict(DEFAULT_SIGNAL_WEIGHTS)
        merged.update(self.weights)
        for alias, canonical in SIGNAL_ALIASES.items():
            if alias in self.weights and canonical not in merged:
                merged[canonical] = self.weights[alias]
            if canonical in merged and alias not in merged:
                merged[alias] = merged[canonical]
        self.weights = merged

    def get(self, signal: str) -> float:
        canonical = SIGNAL_ALIASES.get(signal, signal)
        if canonical in self.weights:
            return self.weights[canonical]
        if signal in self.weights:
            return self.weights[signal]
        raise KeyError(f"Unknown signal weight: {signal}")

    def as_dict(self) -> Dict[str, float]:
        return dict(self.weights)

    def learned_weights(self) -> Dict[str, float]:
        return {
            name: self.get(name)
            for name in LEARNING_SIGNAL_DEFAULTS
        }
