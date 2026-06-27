"""Re-export canonical Big Road engine from road_engine."""

from road_engine import RoadEngine


class BigRoadEngine:
    ROWS = RoadEngine.ROWS

    def __init__(self, history=None):
        self.history = history or []

    def load(self, history):
        self.history = history

    def build(self):
        return RoadEngine(self.history).build_bigroad()

    def clear(self):
        self.history = []
