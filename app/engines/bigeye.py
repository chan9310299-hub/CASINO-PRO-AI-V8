class BigEyeRoad:

    def __init__(self, bigroad):
        self.bigroad = bigroad

    def build(self):

        road = []

        if len(self.bigroad) < 2:
            return road

        for i in range(1, len(self.bigroad)):

            cur = self.bigroad[i]
            prev = self.bigroad[i - 1]

            # 새로운 열 시작
            if cur["row"] == 0:

                if cur["col"] <= 1:
                    continue

                left = self._column_height(cur["col"] - 1)
                left2 = self._column_height(cur["col"] - 2)

                if left == left2:
                    road.append("R")
                else:
                    road.append("B")

            else:

                left = self._has_cell(cur["row"], cur["col"] - 1)

                if left:
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