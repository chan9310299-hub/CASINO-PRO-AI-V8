"""
Independent baccarat road reference (test-only).

Implements Interblock Baccarat Game Description v2.3.1 rules without
importing application modules. Used to compute expected outputs for
validation cases.
"""

ROWS = 6


def normalize_bigroad(cells):
    """Canonical tuple form: (row, col, result, ties, tie_only)."""
    out = []
    for cell in cells:
        out.append((
            cell["row"],
            cell["col"],
            cell.get("result"),
            cell.get("ties", 0),
            bool(cell.get("tie_only", False)),
        ))
    return tuple(out)


def build_bigroad_reference(history):
    board = {}
    road = []

    last_result = None
    last_cell_index = None
    row = 0
    col = 0
    tail_mode = False

    for result in history:
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
                cell = board[(0, 0)]
                cell["result"] = result
                cell["tie_only"] = False
                last_result = result
                last_cell_index = 0
                continue

            row, col, tail_mode = 0, 0, False

        elif result != last_result:
            col = _next_start_col(board)
            row, tail_mode = 0, False

        else:
            if not tail_mode:
                next_row = row + 1
                if next_row < ROWS and (next_row, col) not in board:
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

    return normalize_bigroad(road)


def _next_start_col(board):
    col = 0
    while (0, col) in board:
        col += 1
    return col


def _cell_result(board, row, col):
    cell = board.get((row, col))
    if cell is None:
        return None
    return cell.get("result")


def _column_height(board, col):
    if col < 0:
        return 0
    return sum(1 for (_, c) in board if c == col)


def _iter_placements_reference(history):
    board = {}
    road = []

    last_result = None
    last_cell_index = None
    row = 0
    col = 0
    tail_mode = False

    for result in history:
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
            col = _next_start_col(board)
            row, tail_mode = 0, False

        else:
            if not tail_mode:
                next_row = row + 1
                if next_row < ROWS and (next_row, col) not in board:
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


def _same_column_mark(board, row, col, compare_offset):
    left = _cell_result(board, row, col - compare_offset)
    above_left = _cell_result(board, row - 1, col - compare_offset)
    return "R" if left == above_left else "B"


def _color_for_event(event, compare_offset):
    board = event["board"]
    placement = event.get("placement")

    if event["result"] == "T":
        last_cell = event.get("last_cell")
        if last_cell is None:
            return "R"
        return _same_column_mark(
            board, last_cell["row"], last_cell["col"], compare_offset
        )

    row, col = placement["row"], placement["col"]

    if event["new_column"]:
        left = _column_height(board, col - 1)
        right = _column_height(board, col - 1 - compare_offset)
        return "R" if left == right else "B"

    return _same_column_mark(board, row, col, compare_offset)


def _place_mark(mark, row, col, tail_mode, last_mark, grid_board):
    if last_mark is None:
        row, col, tail_mode = 0, 0, False
    elif mark != last_mark:
        col = _next_start_col(grid_board)
        row, tail_mode = 0, False
    else:
        if not tail_mode:
            next_row = row + 1
            if next_row < ROWS and (next_row, col) not in grid_board:
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

    grid_board[(row, col)] = mark
    return row, col, tail_mode, mark


def build_derived_reference(history, *, start_trigger_col, compare_offset):
    marks = []
    grid_board = {}

    pending_start = False
    started = False

    mark_row = 0
    mark_col = 0
    mark_tail = False
    last_mark = None

    for event in _iter_placements_reference(history):
        if not started and pending_start:
            started = True

        if started:
            mark = _color_for_event(event, compare_offset)
            marks.append(mark)
            mark_row, mark_col, mark_tail, last_mark = _place_mark(
                mark, mark_row, mark_col, mark_tail, last_mark, grid_board
            )

        placement = event.get("placement")
        if (
            placement
            and placement["col"] == start_trigger_col
            and placement["row"] == 0
        ):
            pending_start = True

    return tuple(marks)


def build_big_eye_reference(history):
    return build_derived_reference(
        history, start_trigger_col=1, compare_offset=1
    )


def build_small_road_reference(history):
    return build_derived_reference(
        history, start_trigger_col=2, compare_offset=2
    )


def build_cockroach_reference(history):
    return build_derived_reference(
        history, start_trigger_col=3, compare_offset=3
    )


def build_all_reference(history):
    return {
        "bigroad": build_bigroad_reference(history),
        "big_eye": build_big_eye_reference(history),
        "small_road": build_small_road_reference(history),
        "cockroach": build_cockroach_reference(history),
    }
