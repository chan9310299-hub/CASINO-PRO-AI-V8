from derived_road import build_big_eye


class BigEyeRoad:

    def __init__(self, bigroad=None, history=None):
        self.bigroad = bigroad
        self.history = history

    def build(self):
        history = self._resolve_history()
        return build_big_eye(history)["marks"]

    def build_grid(self):
        history = self._resolve_history()
        return build_big_eye(history)["grid"]

    def build_full(self):
        history = self._resolve_history()
        return build_big_eye(history)

    def _resolve_history(self):
        if self.history is not None:
            return self.history
        if self.bigroad:
            return [cell["result"] for cell in self.bigroad if cell.get("result")]
        return []
