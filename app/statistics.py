class StatisticsEngine:
    def __init__(self, predictions):
        self.predictions = predictions
        self.stats = self.calculate()

    def calculate(self):
        win_streak = 0
        lose_streak = 0
        max_win = 0
        max_lose = 0
        correct = 0
        wrong = 0
        last_result = "-"

        for row in self.predictions:
            prediction, real_result, confidence, is_correct = row

            if real_result not in ("P", "B"):
                continue

            if int(is_correct) == 1:
                correct += 1
                win_streak += 1
                lose_streak = 0
                max_win = max(max_win, win_streak)
                last_result = "적중"
            else:
                wrong += 1
                lose_streak += 1
                win_streak = 0
                max_lose = max(max_lose, lose_streak)
                last_result = "실패"

        total = correct + wrong
        accuracy = round((correct / total) * 100, 2) if total > 0 else 0.0

        return {
            "win_streak": win_streak,
            "lose_streak": lose_streak,
            "max_win": max_win,
            "max_lose": max_lose,
            "correct": correct,
            "wrong": wrong,
            "accuracy": accuracy,
            "last_result": last_result,
            "total": total
        }

    def get(self):
        return self.stats