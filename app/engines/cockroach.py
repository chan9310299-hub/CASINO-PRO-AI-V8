class CockroachRoad:

    def __init__(self, bigroad):
        self.bigroad = bigroad

    def build(self):

        road = []

        if len(self.bigroad) < 4:
            return road

        for i in range(1, len(self.bigroad)):

            cur = self.bigroad[i]

            # Cockroach Road는 4열 이후부터 생성
            if cur["col"] < 4:
                continue

            if cur["row"] == 0:

                left1 = self._column_height(cur["col"] - 1)
                left4 = self._column_height(cur["col"] - 4)

                if left1 == left4:
                    road.append("R")
                else:
                    road.append("B")

            else:

                if self._has_cell(cur["row"], cur["col"] - 3):
                    road.append("R")
                else:
                    road.append("B")

        return road

    def _column_height(self, col):

        h = 0

        for cell in self.bigroad:
            if cell["col"] == col:
                h += 1

        return h

    def _has_cell(self, row, col):

        for cell in self.bigroad:
            if cell["row"] == row and cell["col"] == col:
                return True

        return False