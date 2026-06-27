"""
Deterministic road validation cases (100+).

Each case dict contains:
  - id: unique identifier
  - category: primary test theme
  - history: list of P/B/T
  - expected_bigroad: tuple of (row, col, result, ties, tie_only)
  - expected_big_eye: tuple of R/B marks
  - expected_small_road: tuple of R/B marks
  - expected_cockroach: tuple of R/B marks
"""

from road_rules_reference import build_all_reference


def _case(case_id, category, history):
    expected = build_all_reference(history)
    return {
        "id": case_id,
        "category": category,
        "history": list(history),
        "expected_bigroad": expected["bigroad"],
        "expected_big_eye": expected["big_eye"],
        "expected_small_road": expected["small_road"],
        "expected_cockroach": expected["cockroach"],
    }


def _hand_crafted_cases():
    cases = []

    # --- Big Road placement ---
    cases.append(_case("br_single_player", "bigroad_placement", ["P"]))
    cases.append(_case("br_single_banker", "bigroad_placement", ["B"]))
    cases.append(_case("br_two_column", "bigroad_placement", ["P", "B"]))
    cases.append(_case("br_stack_three", "bigroad_placement", ["P", "P", "P"]))
    cases.append(_case("br_stack_and_turn", "bigroad_placement", ["P", "P", "B"]))
    cases.append(_case("br_multi_column", "bigroad_placement", ["P", "B", "P", "B", "P"]))
    cases.append(_case("br_deep_stack", "bigroad_placement", ["B", "B", "B", "B", "B"]))
    cases.append(_case("br_wgm_sample", "bigroad_placement",
                       ["B", "P", "P", "P", "B", "B", "P", "P", "B", "T"]))

    # --- Tie handling ---
    cases.append(_case("tie_mid_streak", "tie_handling", ["P", "T"]))
    cases.append(_case("tie_double_mid", "tie_handling", ["P", "T", "T"]))
    cases.append(_case("tie_after_stack", "tie_handling", ["P", "P", "T"]))
    cases.append(_case("tie_first_hand", "tie_handling", ["T", "P"]))
    cases.append(_case("tie_first_multi", "tie_handling", ["T", "T", "B"]))
    cases.append(_case("tie_between_columns", "tie_handling", ["P", "B", "T", "B"]))
    cases.append(_case("tie_only_start", "tie_handling", ["T"]))
    cases.append(_case("tie_ping_pong", "tie_handling", ["P", "T", "B", "T", "P"]))
    cases.append(_case("tie_after_dragon", "tie_handling", ["P"] * 6 + ["T"]))
    cases.append(_case("tie_trailing", "tie_handling", ["P", "B", "P", "T", "T", "T"]))

    # --- Dragon ---
    for length in range(6, 13):
        cases.append(_case(
            f"dragon_player_{length}",
            "dragon",
            ["P"] * length,
        ))
    for length in range(6, 13):
        cases.append(_case(
            f"dragon_banker_{length}",
            "dragon",
            ["B"] * length,
        ))
    cases.append(_case("dragon_then_break", "dragon", ["P"] * 8 + ["B"]))
    cases.append(_case("dragon_double_segment", "dragon",
                       ["P"] * 7 + ["B", "B", "B", "B", "B", "B", "B"]))

    # --- Ping Pong ---
    for pairs in range(2, 9):
        seq = []
        for _ in range(pairs):
            seq.extend(["P", "B"])
        cases.append(_case(f"ping_pong_pb_{pairs}", "ping_pong", seq))

    for pairs in range(2, 9):
        seq = []
        for _ in range(pairs):
            seq.extend(["B", "P"])
        cases.append(_case(f"ping_pong_bp_{pairs}", "ping_pong", seq))

    cases.append(_case("ping_pong_with_ties", "ping_pong",
                       ["P", "B", "T", "P", "B", "T", "P", "B"]))

    # --- Big Eye Boy (focused sequences) ---
    cases.append(_case("bigeye_start_gate", "big_eye", ["P", "B", "P"]))
    cases.append(_case("bigeye_depth_blue", "big_eye", ["P", "B", "B"]))
    cases.append(_case("bigeye_depth_red", "big_eye", ["P", "B", "B", "B"]))
    cases.append(_case("bigeye_equal_depth_red", "big_eye", ["P", "B", "P", "B"]))
    cases.append(_case("bigeye_unequal_depth_blue", "big_eye", ["P", "B", "B", "P"]))
    cases.append(_case("bigeye_tie_mark", "big_eye", ["P", "B", "T"]))
    cases.append(_case("bigeye_long_run", "big_eye",
                       ["P", "B", "P", "B", "P", "B", "P", "B", "P", "B"]))

    # --- Small Road ---
    cases.append(_case("small_start_gate", "small_road", ["P", "B", "P", "B"]))
    cases.append(_case("small_depth_sequence", "small_road",
                       ["P", "B", "P", "B", "B", "B"]))
    cases.append(_case("small_with_tie", "small_road",
                       ["P", "B", "P", "B", "T", "P"]))
    cases.append(_case("small_four_columns", "small_road",
                       ["P", "B", "P", "B", "P", "B", "P"]))
    cases.append(_case("small_banker_streak", "small_road",
                       ["B", "P", "B", "P", "B", "B", "B", "P"]))

    # --- Cockroach Pig ---
    cases.append(_case("cockroach_start_gate", "cockroach", ["P", "B", "P", "B", "P"]))
    cases.append(_case("cockroach_depth_sequence", "cockroach",
                       ["P", "B", "P", "B", "P", "B", "B", "B"]))
    cases.append(_case("cockroach_with_tie", "cockroach",
                       ["P", "B", "P", "B", "P", "T", "B"]))
    cases.append(_case("cockroach_five_columns", "cockroach",
                       ["P", "B", "P", "B", "P", "B", "P", "B", "P"]))
    cases.append(_case("cockroach_long_shoe", "cockroach",
                       ["B", "B", "P", "P", "B", "P", "B", "P", "B", "P", "B", "P"]))

    return cases


def _generated_cases():
    cases = []
    idx = 0

    # Deterministic pattern library (seeded by index, not random module)
    patterns = [
        lambda i: (["P", "B"] * (3 + i % 5))[:6 + i % 8],
        lambda i: (["B", "P"] * (3 + i % 5))[:6 + i % 8],
        lambda i: ["P"] * (2 + i % 6) + ["B"] * (1 + i % 4),
        lambda i: ["B"] * (2 + i % 6) + ["P"] * (1 + i % 4),
        lambda i: sum([["P", "P", "B"] for _ in range(1 + i % 4)], []),
        lambda i: sum([["B", "B", "P"] for _ in range(1 + i % 4)], []),
        lambda i: ["P", "B", "B", "P"] * (1 + i % 3),
        lambda i: ["B", "P", "P", "B"] * (1 + i % 3),
    ]

    tie_positions = [0, 1, 2, 3, None, None, None]

    for i in range(50):
        base = patterns[i % len(patterns)](i)
        tie_at = tie_positions[i % len(tie_positions)]
        history = list(base)
        if tie_at is not None and tie_at < len(history):
            history.insert(tie_at, "T")
        idx += 1
        cases.append(_case(f"gen_pattern_{idx:03d}", "generated", history))

    # Fixed-length shoes with mixed outcomes
    alphabet = ["P", "B", "T"]
    for i in range(30):
        length = 5 + (i % 20)
        history = []
        for j in range(length):
            history.append(alphabet[(i * 7 + j * 3) % 3])
        # Ensure at least one P/B for meaningful roads
        if not any(x in ("P", "B") for x in history):
            history[0] = "P"
        idx += 1
        cases.append(_case(f"gen_mixed_{idx:03d}", "generated", history))

    return cases


def build_validation_cases():
    crafted = _hand_crafted_cases()
    generated = _generated_cases()
    all_cases = crafted + generated

    seen_ids = set()
    for case in all_cases:
        if case["id"] in seen_ids:
            raise ValueError(f"Duplicate case id: {case['id']}")
        seen_ids.add(case["id"])

    return all_cases


VALIDATION_CASES = build_validation_cases()

CATEGORY_INDEX = {
    "bigroad_placement": [],
    "tie_handling": [],
    "dragon": [],
    "ping_pong": [],
    "big_eye": [],
    "small_road": [],
    "cockroach": [],
    "generated": [],
}

for _case_data in VALIDATION_CASES:
    CATEGORY_INDEX[_case_data["category"]].append(_case_data["id"])
