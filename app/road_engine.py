class RoadEngine:
    ROWS = 6

    def __init__(self, history):
        self.history = history

    def build_bigroad(self):
        board = {}
        road = []

        last_result = None
        last_cell_index = None
        row = 0
        col = 0
        tail_mode = False

        for result in self.history:
            if result == "T":
                if last_cell_index is not None:
                    road[last_cell_index]["ties"] += 1
                elif (0, 0) not in board:
                    cell = {
                        "result": None,
                        "row": 0,
                        "col": 0,
                        "ties": 1,
                        "tie_only": True,
                    }
                    board[(0, 0)] = cell
                    road.append(cell)
                    last_cell_index = 0
                else:
                    road[last_cell_index]["ties"] += 1
                continue

            if result not in ("P", "B"):
                continue

            if last_result is None:
                if (0, 0) in board and board[(0, 0)].get("tie_only"):
                    row, col, tail_mode = 0, 0, False
                    cell = board[(0, 0)]
                    cell["result"] = result
                    cell["tie_only"] = False
                    last_result = result
                    last_cell_index = 0
                    continue

                row, col, tail_mode = 0, 0, False

            elif result != last_result:
                col = self.next_start_col(board)
                row, tail_mode = 0, False

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
            last_cell_index = len(road) - 1

        return road

    def next_start_col(self, board):
        col = 0
        while (0, col) in board:
            col += 1
        return col

    @staticmethod
    def cell_result(board, row, col):
        cell = board.get((row, col))
        if cell is None:
            return None
        return cell.get("result")

    @staticmethod
    def column_height(board, col):
        if col < 0:
            return 0
        return sum(1 for (_, c) in board if c == col)

    def iter_placements(self):
        """Yield one event per hand for derived-road generation."""
        board = {}
        road = []

        last_result = None
        last_cell_index = None
        row = 0
        col = 0
        tail_mode = False

        for result in self.history:
            if result == "T":
                if last_cell_index is not None:
                    road[last_cell_index]["ties"] += 1
                elif (0, 0) not in board:
                    cell = {
                        "result": None,
                        "row": 0,
                        "col": 0,
                        "ties": 1,
                        "tie_only": True,
                    }
                    board[(0, 0)] = cell
                    road.append(cell)
                    last_cell_index = 0

                yield {
                    "result": "T",
                    "board": dict(board),
                    "last_cell": road[last_cell_index] if last_cell_index is not None else None,
                    "placement": None,
                    "new_column": False,
                }
                continue

            if result not in ("P", "B"):
                continue

            new_column = last_result is None or result != last_result

            if last_result is None:
                if (0, 0) in board and board[(0, 0)].get("tie_only"):
                    row, col, tail_mode = 0, 0, False
                    cell = board[(0, 0)]
                    cell["result"] = result
                    cell["tie_only"] = False
                    last_result = result
                    last_cell_index = 0

                    yield {
                        "result": result,
                        "board": dict(board),
                        "last_cell": cell,
                        "placement": {"row": row, "col": col},
                        "new_column": True,
                    }
                    continue

                row, col, tail_mode = 0, 0, False

            elif result != last_result:
                col = self.next_start_col(board)
                row, tail_mode = 0, False

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
            last_cell_index = len(road) - 1

            yield {
                "result": result,
                "board": dict(board),
                "last_cell": cell,
                "placement": {"row": row, "col": col},
                "new_column": new_column and row == 0,
            }
