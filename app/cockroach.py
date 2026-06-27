from derived_road import build_cockroach_road


class CockroachRoad:

    def __init__(self, bigroad=None, history=None):
        self.bigroad = bigroad
        self.history = history

    def build(self):
        history = self._resolve_history()
        return build_cockroach_road(history)["marks"]

    def build_grid(self):
        history = self._resolve_history()
        return build_cockroach_road(history)["grid"]

    def build_full(self):
        history = self._resolve_history()
        return build_cockroach_road(history)

    def _resolve_history(self):
        if self.history is not None:
            return self.history
        if self.bigroad:
            return [cell["result"] for cell in self.bigroad if cell.get("result")]
        return []
