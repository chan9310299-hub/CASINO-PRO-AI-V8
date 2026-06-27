from collections import Counter


class AIEngine:
    def __init__(self, history):
        self.history = history
        self.pb = [x for x in history if x in ("P", "B")]

    def predict(self):
        if len(self.pb) < 6:
            return None, 0.0, "6개 입력 후 7번째부터 예측 시작"

        score = {"P": 1.0, "B": 1.0}
        reasons = []

        # 최근 흐름
        for size, weight in [(6, 1.0), (12, 1.5), (24, 2.0)]:
            recent = self.pb[-size:]
            c = Counter(recent)
            total = c["P"] + c["B"]

            if total > 0:
                score["P"] += (c["P"] / total) * weight
                score["B"] += (c["B"] / total) * weight

        # 패턴 분석 1~8
        for size in range(1, 9):
            if len(self.pb) <= size:
                continue

            pattern = tuple(self.pb[-size:])
            result = {"P": 0, "B": 0}

            for i in range(len(self.pb) - size):
                if tuple(self.pb[i:i + size]) == pattern:
                    nxt = self.pb[i + size]
                    result[nxt] += 1

            total = result["P"] + result["B"]

            if total > 0:
                weight = 1.0 + size * 0.35
                score["P"] += (result["P"] / total) * weight
                score["B"] += (result["B"] / total) * weight

                winner = "P" if result["P"] >= result["B"] else "B"
                reasons.append(f"{size}패턴 → {winner}")

        # 연속 보정
        last = self.pb[-1]
        streak = 0

        for x in reversed(self.pb):
            if x == last:
                streak += 1
            else:
                break

        opposite = "B" if last == "P" else "P"

        if streak >= 5:
            score[opposite] += 2.0
            reasons.append(f"{last} {streak}연속 → 반대 보정")
        elif streak >= 3:
            score[opposite] += 1.0
            reasons.append(f"{last} {streak}연속 → 꺾임 주의")
        else:
            reasons.append("연속 흐름 정상")

        pred = "P" if score["P"] >= score["B"] else "B"

        high = max(score["P"], score["B"])
        low = min(score["P"], score["B"])
        confidence = round((high - low) / high, 3) if high > 0 else 0.0

        if confidence < 0.08:
            status = "위험 / 패스 추천"
        elif confidence < 0.18:
            status = "주의"
        else:
            status = "정상"

        return pred, confidence, status