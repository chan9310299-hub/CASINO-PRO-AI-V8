"""
Weighted baccarat prediction engine.

Each signal produces a raw P/B bias, multiplied by an adjustable weight
from ScoringConfig, then summed into the final weighted score.
"""

from collections import Counter
from typing import Any, Callable, Dict, List, Optional, Tuple

from ai.scoring_config import ScoringConfig, DEFAULT_SIGNAL_WEIGHTS

MIN_PREDICT_COUNT = 6


class PredictionEngine:
    """Single source of truth for AI prediction logic."""

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        pattern_memory_lookup: Optional[Callable[[List[str]], Dict[str, Any]]] = None,
    ):
        self.config = ScoringConfig(weights=weights or {})
        self.pattern_memory_lookup = pattern_memory_lookup or (
            lambda _pb: {"active": False}
        )

    def analyze(
        self,
        history,
        bigroad=None,
        bigeye=None,
        smallroad=None,
        cockroach=None,
    ):
        pb = [x for x in history if x in ("P", "B")]

        if len(pb) < MIN_PREDICT_COUNT:
            return self._insufficient_data()

        signal_breakdown: Dict[str, Dict[str, Any]] = {}
        reason_in_korean: List[str] = []

        weighted_score = {
            "P": self.config.get("base_p"),
            "B": self.config.get("base_b"),
        }

        collectors = [
            lambda: self._collect_recent(pb, 10, "recent_10", signal_breakdown, reason_in_korean),
            lambda: self._collect_recent(pb, 20, "recent_20", signal_breakdown, reason_in_korean),
            lambda: self._collect_recent(pb, 30, "recent_30", signal_breakdown, reason_in_korean),
            lambda: self._collect_bigroad(bigroad, pb, signal_breakdown, reason_in_korean),
            lambda: self._collect_dragon(pb, signal_breakdown, reason_in_korean),
            lambda: self._collect_chop(pb, signal_breakdown, reason_in_korean),
            lambda: self._collect_ping_pong(pb, signal_breakdown, reason_in_korean),
            lambda: self._collect_double_pattern(pb, signal_breakdown, reason_in_korean),
            lambda: self._collect_big_eye(bigroad, pb, bigeye, signal_breakdown, reason_in_korean),
            lambda: self._collect_small_road(bigroad, pb, smallroad, signal_breakdown, reason_in_korean),
            lambda: self._collect_cockroach_road(bigroad, pb, cockroach, signal_breakdown, reason_in_korean),
            lambda: self._collect_pattern_memory(pb, signal_breakdown, reason_in_korean),
        ]

        for collect in collectors:
            raw_p, raw_b = collect()
            self._apply_weighted_signal(
                weighted_score,
                raw_p,
                raw_b,
            )

        prediction = "B" if weighted_score["B"] > weighted_score["P"] else "P"
        confidence = self._confidence(weighted_score)
        status = self._status(prediction, confidence, weighted_score)
        learned_weights = self.config.learned_weights()

        return {
            "prediction": prediction,
            "confidence": confidence,
            "weighted_score": dict(weighted_score),
            "signal_breakdown": signal_breakdown,
            "reason_in_korean": reason_in_korean,
            "score": dict(weighted_score),
            "reason": reason_in_korean,
            "status": status,
            "learned_weights": learned_weights,
        }

    def _insufficient_data(self):
        empty_score = {"P": 0.0, "B": 0.0}
        return {
            "prediction": None,
            "confidence": 0,
            "weighted_score": empty_score,
            "signal_breakdown": {},
            "reason_in_korean": ["데이터 부족"],
            "score": empty_score,
            "reason": ["데이터 부족"],
            "status": "6개 입력 후 7번째부터 예측 시작",
            "learned_weights": self.config.learned_weights(),
        }

    def _record_signal(
        self,
        name: str,
        raw_p: float,
        raw_b: float,
        weight: float,
        weighted_p: float,
        weighted_b: float,
        active: bool,
        reason: Optional[str],
        breakdown: Dict[str, Dict[str, Any]],
        reasons: List[str],
    ):
        breakdown[name] = {
            "raw": {"P": round(raw_p, 4), "B": round(raw_b, 4)},
            "weight": weight,
            "weighted": {"P": round(weighted_p, 4), "B": round(weighted_b, 4)},
            "active": active,
        }
        if active and reason:
            reasons.append(reason)

    def _apply_weighted_signal(
        self,
        weighted_score: Dict[str, float],
        raw_p: float,
        raw_b: float,
    ):
        weighted_score["P"] += raw_p
        weighted_score["B"] += raw_b

    def _finalize_signal(
        self,
        name: str,
        raw_p: float,
        raw_b: float,
        reason: Optional[str],
        breakdown: Dict[str, Dict[str, Any]],
        reasons: List[str],
    ) -> Tuple[float, float]:
        weight = self.config.get(name)
        weighted_p = raw_p * weight
        weighted_b = raw_b * weight
        active = raw_p > 0 or raw_b > 0
        self._record_signal(
            name, raw_p, raw_b, weight, weighted_p, weighted_b,
            active, reason, breakdown, reasons,
        )
        return weighted_p, weighted_b

    def _collect_recent(
        self,
        pb: List[str],
        window: int,
        signal_name: str,
        breakdown: Dict[str, Dict[str, Any]],
        reasons: List[str],
    ) -> Tuple[float, float]:
        segment = pb[-window:]
        counts = Counter(segment)
        total = counts["P"] + counts["B"]
        if total == 0:
            return self._finalize_signal(signal_name, 0.0, 0.0, None, breakdown, reasons)

        raw_p = counts["P"] / total
        raw_b = counts["B"] / total

        p_ratio = raw_p
        if p_ratio >= 0.6:
            reason = f"최근 {window}판 PLAYER 우세 ({counts['P']}/{total})"
        elif p_ratio <= 0.4:
            reason = f"최근 {window}판 BANKER 우세 ({counts['B']}/{total})"
        else:
            reason = f"최근 {window}판 균형 (P:{counts['P']} B:{counts['B']})"

        return self._finalize_signal(signal_name, raw_p, raw_b, reason, breakdown, reasons)

    def _collect_bigroad(
        self,
        bigroad,
        pb: List[str],
        breakdown: Dict[str, Dict[str, Any]],
        reasons: List[str],
    ) -> Tuple[float, float]:
        if not bigroad:
            return self._finalize_signal(
                "bigroad", 0.0, 0.0, None, breakdown, reasons
            )

        last_cell = bigroad[-1]
        last_result = last_cell.get("result") or pb[-1]
        if last_result not in ("P", "B"):
            return self._finalize_signal(
                "bigroad", 0.0, 0.0, None, breakdown, reasons
            )

        col_depth = sum(1 for cell in bigroad if cell["col"] == last_cell["col"])
        raw_p = 1.0 + min(col_depth * 0.15, 0.6) if last_result == "P" else 0.0
        raw_b = 1.0 + min(col_depth * 0.15, 0.6) if last_result == "B" else 0.0

        reason = f"BigRoad 현재열 {col_depth}칸 → {last_result} 추세"
        return self._finalize_signal(
            "bigroad", raw_p, raw_b, reason, breakdown, reasons
        )

    def _streak_length(self, pb: List[str]) -> Tuple[str, int]:
        last = pb[-1]
        streak = 1
        for i in range(len(pb) - 2, -1, -1):
            if pb[i] == last:
                streak += 1
            else:
                break
        return last, streak

    def _collect_dragon(
        self,
        pb: List[str],
        breakdown: Dict[str, Dict[str, Any]],
        reasons: List[str],
    ) -> Tuple[float, float]:
        last, streak = self._streak_length(pb)
        opposite = "B" if last == "P" else "P"

        raw_p = 0.0
        raw_b = 0.0

        if streak >= 6:
            strength = 1.0 + min((streak - 5) * 0.15, 0.75)
            if last == "P":
                raw_p += strength
            else:
                raw_b += strength
            reason = f"드래곤 {last} {streak}연속 → 추종"
        elif streak >= 4:
            strength = 0.75 + (streak - 3) * 0.1
            if last == "P":
                raw_p += strength
            else:
                raw_b += strength
            reason = f"장줄 {last} {streak}연속 → 추종"
        elif streak >= 2:
            strength = 0.4
            if last == "P":
                raw_p += strength
            else:
                raw_b += strength
            reason = f"{last} {streak}연속 → 흐름 유지"
        else:
            return self._finalize_signal("dragon", 0.0, 0.0, None, breakdown, reasons)

        if streak >= 5:
            hedge = 0.35
            if opposite == "P":
                raw_p += hedge
            else:
                raw_b += hedge
            reason = f"{reason} + 반전 보정({opposite})"

        return self._finalize_signal("dragon", raw_p, raw_b, reason, breakdown, reasons)

    def _is_chop(self, seq: List[str]) -> bool:
        if len(seq) < 4:
            return False
        return all(seq[i] != seq[i + 1] for i in range(len(seq) - 1))

    def _collect_chop(
        self,
        pb: List[str],
        breakdown: Dict[str, Dict[str, Any]],
        reasons: List[str],
    ) -> Tuple[float, float]:
        for window in (6, 8, 10):
            if len(pb) < window:
                continue
            segment = pb[-window:]
            if self._is_chop(segment):
                nxt = "B" if pb[-1] == "P" else "P"
                raw_p = 1.0 if nxt == "P" else 0.0
                raw_b = 1.0 if nxt == "B" else 0.0
                reason = f"줄타기(교대) {window}판 → {nxt}"
                return self._finalize_signal("chop", raw_p, raw_b, reason, breakdown, reasons)

        return self._finalize_signal("chop", 0.0, 0.0, None, breakdown, reasons)

    def _collect_ping_pong(
        self,
        pb: List[str],
        breakdown: Dict[str, Dict[str, Any]],
        reasons: List[str],
    ) -> Tuple[float, float]:
        patterns = [
            (["P", "B", "P", "B"], "P"),
            (["B", "P", "B", "P"], "B"),
            (["P", "B", "P", "B", "P", "B"], "P"),
            (["B", "P", "B", "P", "B", "P"], "B"),
        ]

        for pattern, nxt in patterns:
            size = len(pattern)
            if len(pb) >= size and pb[-size:] == pattern:
                raw_p = 1.0 if nxt == "P" else 0.0
                raw_b = 1.0 if nxt == "B" else 0.0
                reason = f"핑퐁 {size}패턴 → {nxt}"
                return self._finalize_signal(
                    "ping_pong", raw_p, raw_b, reason, breakdown, reasons
                )

        return self._finalize_signal("ping_pong", 0.0, 0.0, None, breakdown, reasons)

    def _collect_double_pattern(
        self,
        pb: List[str],
        breakdown: Dict[str, Dict[str, Any]],
        reasons: List[str],
    ) -> Tuple[float, float]:
        if len(pb) >= 4:
            a, b, c, d = pb[-4:]
            if a == b and c == d and a != c:
                side = d
                raw_p = 1.0 if side == "P" else 0.0
                raw_b = 1.0 if side == "B" else 0.0
                reason = f"더블 패턴 {a}{b}|{c}{d} → {side}"
                return self._finalize_signal(
                    "double_pattern", raw_p, raw_b, reason, breakdown, reasons
                )

        if len(pb) >= 2 and pb[-1] == pb[-2]:
            side = pb[-1]
            raw_p = 0.75 if side == "P" else 0.0
            raw_b = 0.75 if side == "B" else 0.0
            reason = f"더블 패턴 {side}{side} → {side}"
            return self._finalize_signal(
                "double_pattern", raw_p, raw_b, reason, breakdown, reasons
            )

        return self._finalize_signal("double_pattern", 0.0, 0.0, None, breakdown, reasons)

    def _collect_pattern_memory(
        self,
        pb: List[str],
        breakdown: Dict[str, Dict[str, Any]],
        reasons: List[str],
    ) -> Tuple[float, float]:
        mem = self.pattern_memory_lookup(pb)
        if not mem.get("active"):
            return self._finalize_signal(
                "pattern_memory", 0.0, 0.0, None, breakdown, reasons
            )

        raw_p = mem.get("raw_p", 0.0)
        raw_b = mem.get("raw_b", 0.0)
        reason = mem.get("reason")
        return self._finalize_signal(
            "pattern_memory", raw_p, raw_b, reason, breakdown, reasons
        )

    def _collect_derived_signal(
        self,
        signal_name: str,
        label: str,
        road,
        br_last: str,
        breakdown: Dict[str, Dict[str, Any]],
        reasons: List[str],
    ) -> Tuple[float, float]:
        if not road:
            return self._finalize_signal(signal_name, 0.0, 0.0, None, breakdown, reasons)

        mark = road[-1]
        if mark == "R":
            raw_p = 1.0 if br_last == "P" else 0.0
            raw_b = 1.0 if br_last == "B" else 0.0
            reason = f"{label} RED → 흐름 유지 ({br_last})"
        else:
            opposite = "B" if br_last == "P" else "P"
            raw_p = 1.0 if opposite == "P" else 0.0
            raw_b = 1.0 if opposite == "B" else 0.0
            reason = f"{label} BLUE → 변동 ({opposite})"

        return self._finalize_signal(signal_name, raw_p, raw_b, reason, breakdown, reasons)

    def _br_last(self, bigroad, pb: List[str]) -> str:
        if bigroad and bigroad[-1].get("result"):
            return bigroad[-1]["result"]
        return pb[-1]

    def _collect_big_eye(self, bigroad, pb, bigeye, breakdown, reasons):
        return self._collect_derived_signal(
            "big_eye", "BigEye", bigeye, self._br_last(bigroad, pb), breakdown, reasons
        )

    def _collect_small_road(self, bigroad, pb, smallroad, breakdown, reasons):
        return self._collect_derived_signal(
            "small_road", "Small", smallroad, self._br_last(bigroad, pb), breakdown, reasons
        )

    def _collect_cockroach_road(self, bigroad, pb, cockroach, breakdown, reasons):
        return self._collect_derived_signal(
            "cockroach_road", "Cockroach", cockroach,
            self._br_last(bigroad, pb), breakdown, reasons,
        )

    def _confidence(self, weighted_score: Dict[str, float]) -> float:
        total = weighted_score["P"] + weighted_score["B"]
        if total <= 0:
            return 0.0
        return round(max(weighted_score.values()) / total, 3)

    def _status(self, prediction, confidence, weighted_score):
        if prediction is None:
            return "6개 입력 후 7번째부터 예측 시작"

        total = weighted_score["P"] + weighted_score["B"]
        if total <= 0:
            return "분석 불가"

        margin = abs(weighted_score["P"] - weighted_score["B"]) / total

        if margin < 0.08:
            return "혼조 구간 — 신뢰도 낮음, 관망 추천"
        if margin < 0.15:
            return "주의 구간 — 신뢰도 보통, 신중 판단"
        if confidence >= 0.6:
            return "정상 구간 — 패턴 신호 강함"
        return "정상 구간 — 패턴 분석 유효"


__all__ = ["PredictionEngine", "MIN_PREDICT_COUNT", "DEFAULT_SIGNAL_WEIGHTS"]
