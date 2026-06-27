from collections import Counter
from config import TIE, PB_RESULTS


class TieEngine:
    def __init__(self, history):
        self.history = history

    def after_tie_results(self):
        results = []

        for i in range(len(self.history) - 1):
            if self.history[i] == TIE:
                nxt = self.history[i + 1]

                if nxt in PB_RESULTS:
                    results.append(nxt)

        return results

    def analyze(self):
        results = self.after_tie_results()

        if not results:
            return {
                "prediction": None,
                "confidence": 0.0,
                "p_count": 0,
                "b_count": 0,
                "message": "타이 이후 패턴 학습 중"
            }

        c = Counter(results)

        p_count = c["P"]
        b_count = c["B"]
        total = p_count + b_count

        if total == 0:
            return {
                "prediction": None,
                "confidence": 0.0,
                "p_count": 0,
                "b_count": 0,
                "message": "타이 이후 패턴 부족"
            }

        prediction = "P" if p_count >= b_count else "B"
        confidence = abs(p_count - b_count) / total

        return {
            "prediction": prediction,
            "confidence": round(confidence, 3),
            "p_count": p_count,
            "b_count": b_count,
            "message": "타이 이후 흐름 분석 완료"
        }