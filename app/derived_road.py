"""Official derived-road logic (Big Eye Boy, Small Road, Cockroach Pig).

Rules reference: Interblock Baccarat Game Description v2.3.1.
Red = pattern regularity; Blue = change. Neither maps to Player/Banker.
"""

from road_engine import RoadEngine


class DerivedRoadBuilder:
    ROWS = 6

    def __init__(self, history, *, start_trigger_col, compare_offset):
        self.history = history
        self.start_trigger_col = start_trigger_col
        self.compare_offset = compare_offset

    def build(self):
        marks = []
        grid = []
        grid_board = {}

        pending_start = False
        started = False

        mark_row = 0
        mark_col = 0
        mark_tail = False
        last_mark = None

        for event in RoadEngine(self.history).iter_placements():
            if not started and pending_start:
                started = True

            if started:
                mark = self._color_for_event(event)
                marks.append(mark)

                mark_row, mark_col, mark_tail, last_mark = self._place_mark(
                    mark,
                    mark_row,
                    mark_col,
                    mark_tail,
                    last_mark,
                    grid_board,
                    grid,
                )

            placement = event.get("placement")
            if (
                placement
                and placement["col"] == self.start_trigger_col
                and placement["row"] == 0
            ):
                pending_start = True

        return {"marks": marks, "grid": grid}

    def _color_for_event(self, event):
        board = event["board"]
        placement = event.get("placement")

        if event["result"] == "T":
            last_cell = event.get("last_cell")
            if last_cell is None:
                return "R"
            return self._same_column_mark(
                board, last_cell["row"], last_cell["col"]
            )

        row, col = placement["row"], placement["col"]

        if event["new_column"]:
            left = RoadEngine.column_height(board, col - 1)
            right = RoadEngine.column_height(board, col - 1 - self.compare_offset)
            return "R" if left == right else "B"

        return self._same_column_mark(board, row, col)

    def _same_column_mark(self, board, row, col):
        left = RoadEngine.cell_result(board, row, col - self.compare_offset)
        above_left = RoadEngine.cell_result(board, row - 1, col - self.compare_offset)
        return "R" if left == above_left else "B"

    def _place_mark(
        self,
        mark,
        row,
        col,
        tail_mode,
        last_mark,
        grid_board,
        grid,
    ):
        if last_mark is None:
            row, col, tail_mode = 0, 0, False
        elif mark != last_mark:
            col = self._next_start_col(grid_board)
            row, tail_mode = 0, False
        else:
            if not tail_mode:
                next_row = row + 1
                if next_row < self.ROWS and (next_row, col) not in grid_board:
                    row = next_row
                else:
                    tail_mode = True
                    col += 1
                    while (row, col) in grid_board:
                        col += 1
            else:
                col += 1
                while (row, col) in grid_board:
                    col += 1

        cell = {"mark": mark, "row": row, "col": col}
        grid_board[(row, col)] = cell
        grid.append(cell)
        return row, col, tail_mode, mark

    def _next_start_col(self, grid_board):
        col = 0
        while (0, col) in grid_board:
            col += 1
        return col


def build_big_eye(history):
    return DerivedRoadBuilder(
        history,
        start_trigger_col=1,
        compare_offset=1,
    ).build()


def build_small_road(history):
    return DerivedRoadBuilder(
        history,
        start_trigger_col=2,
        compare_offset=2,
    ).build()


def build_cockroach_road(history):
    return DerivedRoadBuilder(
        history,
        start_trigger_col=3,
        compare_offset=3,
    ).build()
