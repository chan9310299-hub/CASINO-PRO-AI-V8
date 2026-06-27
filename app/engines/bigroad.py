class BigRoadEngine:
    ROWS = 6

    def __init__(self, history):
        self.history = history

    def build(self):
        board = {}
        road = []

        last_result = None
        last_index = None

        row = 0
        col = 0
        tail_mode = False

        for result in self.history:
            if result == "T":
                if last_index is not None:
                    road[last_index]["ties"] += 1
                continue

            if result not in ("P", "B"):
                continue

            if last_result is None:
                row = 0
                col = 0
                tail_mode = False

            elif result != last_result:
                col = self._next_empty_top_col(board)
                row = 0
                tail_mode = False

            else:
                if not tail_mode:
                    next_row = row + 1

                    if next_row < self.ROWS and (next_row, col) not in board:
                        row = next_row
                    else:
                        tail_mode = True
                        col += 1

                        while (row, col) in board:
                            col += 1
                else:
                    col += 1

                    while (row, col) in board:
                        col += 1

            cell = {
                "result": result,
                "row": row,
                "col": col,
                "ties": 0,
            }

            board[(row, col)] = cell
            road.append(cell)

            last_result = result
            last_index = len(road) - 1

        return road

    def _next_empty_top_col(self, board):
        col = 0

        while (0, col) in board:
            col += 1

        return col