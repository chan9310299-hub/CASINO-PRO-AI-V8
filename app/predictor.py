from local_config import MIN_PREDICT_COUNT
from learning import LearningEngine


class Predictor:
    def __init__(self, history):
        self.history = history
        self.learning = LearningEngine(history)

    def predict(self):
        pb = self.learning.pb_history

        if len(pb) < MIN_PREDICT_COUNT:
            return None, 0.0, "학습 중", "6개 입력 후, 7번째부터 예측 시작", []

        scores = {
            "P": 1.0,
            "B": 1.0
        }

        reasons = []

        # 1. 전체 비율
        global_scores = self.learning.global_score()
        scores["P"] += global_scores["P"]
        scores["B"] += global_scores["B"]

        # 2. 최근 흐름
        recent_scores = self.learning.recent_score()
        scores["P"] += recent_scores["P"]
        scores["B"] += recent_scores["B"]

        # 3. 패턴 점수
        pattern_scores, pattern_reasons = self.learning.pattern_score()
        scores["P"] += pattern_scores["P"]
        scores["B"] += pattern_scores["B"]
        reasons.extend(pattern_reasons[-5:])

        # 4. 연속 흐름 보정
        streak_scores, streak_msg = self.learning.streak_score()
        scores["P"] += streak_scores["P"]
        scores["B"] += streak_scores["B"]
        reasons.append(streak_msg)

        # 5. 타이 이후 흐름 보정
        tie_pred, tie_conf, tie_msg = self.learning.tie_prediction()

        if self.history and self.history[-1] == "T" and tie_pred:
            scores[tie_pred] += tie_conf * 2.0
            reasons.append(f"타이 이후 흐름 반영: {tie_pred} 보정")
        else:
            reasons.append(tie_msg)

        pred = "P" if scores["P"] >= scores["B"] else "B"

        high = max(scores["P"], scores["B"])
        low = min(scores["P"], scores["B"])
        confidence = round((high - low) / high, 3) if high > 0 else 0.0

        if confidence < 0.08:
            status = "혼조 구간"
            comment = "신뢰도 낮음. 관망 추천"
        elif confidence < 0.18:
            status = "주의 구간"
            comment = "흐름 약함. 신중 판단"
        else:
            status = "정상 구간"
            comment = "패턴 분석 정상"

        return pred, confidence, status, comment, reasons