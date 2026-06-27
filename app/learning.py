from collections import Counter, defaultdict
from config import PB_RESULTS, TIE, MAX_PATTERN_SIZE


class LearningEngine:
    def __init__(self, history):
        self.history = history
        self.pb_history = self.only_pb(history)

    def only_pb(self, data):
        return [x for x in data if x in PB_RESULTS]

    def count_all(self):
        return Counter(self.history)

    def count_pb(self):
        return Counter(self.pb_history)

    def recent_pb(self, size=30):
        return self.pb_history[-size:]

    def recent_score(self):
        scores = {"P": 0.0, "B": 0.0}

        for window, weight in [
            (12, 1.2),
            (24, 1.5),
            (48, 1.8),
            (100, 2.2)
        ]:
            recent = self.recent_pb(window)
            c = Counter(recent)
            total = c["P"] + c["B"]

            if total > 0:
                scores["P"] += (c["P"] / total) * weight
                scores["B"] += (c["B"] / total) * weight

        return scores

    def global_score(self):
        scores = {"P": 0.0, "B": 0.0}

        c = self.count_pb()
        total = c["P"] + c["B"]

        if total > 0:
            scores["P"] += (c["P"] / total) * 1.0
            scores["B"] += (c["B"] / total) * 1.0

        return scores

    def current_pattern(self, size):
        if len(self.pb_history) < size:
            return None

        return tuple(self.pb_history[-size:])

    def next_after_pattern(self, size):
        result = {"P": 0, "B": 0}

        pattern = self.current_pattern(size)

        if pattern is None:
            return result

        for i in range(len(self.pb_history) - size):
            current = tuple(self.pb_history[i:i + size])
            nxt = self.pb_history[i + size]

            if current == pattern and nxt in PB_RESULTS:
                result[nxt] += 1

        return result

    def pattern_score(self, max_size=MAX_PATTERN_SIZE):
        scores = {"P": 0.0, "B": 0.0}
        reasons = []

        for size in range(1, max_size + 1):
            nxt = self.next_after_pattern(size)
            total = nxt["P"] + nxt["B"]

            if total > 0:
                weight = 0.7 + (size * 0.45)

                p_ratio = nxt["P"] / total
                b_ratio = nxt["B"] / total

                scores["P"] += p_ratio * weight
                scores["B"] += b_ratio * weight

                winner = "P" if p_ratio >= b_ratio else "B"
                confidence = max(p_ratio, b_ratio)

                reasons.append(
                    f"{size}패턴 {''.join(self.current_pattern(size))} → {winner} 우세 ({round(confidence * 100, 1)}%)"
                )

        return scores, reasons

    def streak_info(self):
        if not self.pb_history:
            return {
                "last": None,
                "streak": 0,
                "opposite": None
            }

        last = self.pb_history[-1]
        streak = 0

        for x in reversed(self.pb_history):
            if x == last:
                streak += 1
            else:
                break

        opposite = "B" if last == "P" else "P"

        return {
            "last": last,
            "streak": streak,
            "opposite": opposite
        }

    def streak_score(self):
        scores = {"P": 0.0, "B": 0.0}
        info = self.streak_info()

        last = info["last"]
        streak = info["streak"]
        opposite = info["opposite"]

        if last is None:
            return scores, "연속 흐름 없음"

        if streak >= 5:
            scores[opposite] += 1.8
            msg = f"{last} {streak}연속 → 반대 흐름 {opposite} 보정"
        elif streak >= 3:
            scores[opposite] += 1.0
            msg = f"{last} {streak}연속 → 꺾임 가능성 보정"
        elif streak >= 2:
            scores[last] += 0.5
            msg = f"{last} {streak}연속 → 지속 흐름 보정"
        else:
            msg = "연속 흐름 약함"

        return scores, msg

    def tie_after_flow(self):
        result = {"P": 0, "B": 0}

        for i in range(len(self.history) - 1):
            if self.history[i] == TIE:
                nxt = self.history[i + 1]

                if nxt in PB_RESULTS:
                    result[nxt] += 1

        return result

    def tie_prediction(self):
        flow = self.tie_after_flow()
        total = flow["P"] + flow["B"]

        if total == 0:
            return None, 0.0, "타이 이후 패턴 학습 중"

        pred = "P" if flow["P"] >= flow["B"] else "B"
        confidence = abs(flow["P"] - flow["B"]) / total

        return pred, round(confidence, 3), f"T 이후 P:{flow['P']} / B:{flow['B']}"

    def summary(self):
        c = self.count_all()
        return {
            "total": len(self.history),
            "pb_total": len(self.pb_history),
            "p": c["P"],
            "b": c["B"],
            "t": c["T"]
        }