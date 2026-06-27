class BigEyeRoad:

    def __init__(self, bigroad):
        self.bigroad = bigroad

    def build(self):

        road = []

        if len(self.bigroad) < 2:
            return road

        for cell in self.bigroad:

            if cell["col"] < 2:
                continue

            if cell["row"] == 0:

                left = self.column_height(cell["col"] - 1)
                left2 = self.column_height(cell["col"] - 2)

                if left == left2:
                    road.append("R")
                else:
                    road.append("B")

            else:

                if self.has_cell(cell["row"], cell["col"] - 1):
                    road.append("R")
                else:
                    road.append("B")

        return road

    def column_height(self, col):

        h = 0

        for c in self.bigroad:
            if c["col"] == col:
                h += 1

        return h

    def has_cell(self, row, col):

        for c in self.bigroad:
            if c["row"] == row and c["col"] == col:
                return True

        return False