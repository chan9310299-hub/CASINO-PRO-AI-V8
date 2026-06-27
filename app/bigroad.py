from road_engine import RoadEngine


class BigRoadEngine:
    def __init__(self):
        self.history = []

    def load(self, history):
        self.history = history

    def build(self):
        return RoadEngine(self.history).build_bigroad()

    def clear(self):
        self.history = []