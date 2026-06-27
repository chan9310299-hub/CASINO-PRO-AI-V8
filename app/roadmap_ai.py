from collections import Counter


class RoadmapAI:

    def analyze(
        self,
        history,
        bigroad=None,
        bigeye=None,
        smallroad=None,
        cockroach=None,
    ):

        pb = [x for x in history if x in ("P", "B")]

        if len(pb) < 6:
            return {
                "prediction": None,
                "confidence": 0,
                "reason": ["데이터 부족"],
                "score": {"P": 0, "B": 0},
            }

        score = {
            "P": 0.0,
            "B": 0.0,
        }

        reason = []

        ################################################
        # 최근 20판
        ################################################

        recent = pb[-20:]

        c = Counter(recent)

        score["P"] += c["P"] * 0.6
        score["B"] += c["B"] * 0.6

        if c["P"] > c["B"]:
            reason.append("최근 PLAYER 우세")

        elif c["B"] > c["P"]:
            reason.append("최근 BANKER 우세")

        ################################################
        # BigRoad
        ################################################

        if bigroad:

            last = bigroad[-1]["result"]

            score[last] += 3

            reason.append(f"BigRoad → {last}")

        ################################################
        # BigEye
        ################################################

        if bigeye:

            if bigeye[-1] == "R":

                score["P"] += 1.5
                reason.append("BigEye RED")

            else:

                score["B"] += 1.5
                reason.append("BigEye BLUE")

        ################################################
        # Small Road
        ################################################

        if smallroad:

            if smallroad[-1] == "R":

                score["P"] += 1.5
                reason.append("Small RED")

            else:

                score["B"] += 1.5
                reason.append("Small BLUE")

        ################################################
        # Cockroach
        ################################################

        if cockroach:

            if cockroach[-1] == "R":

                score["P"] += 1.5
                reason.append("Cockroach RED")

            else:

                score["B"] += 1.5
                reason.append("Cockroach BLUE")

        ################################################
        # Dragon 감지
        ################################################

        streak = 1

        for i in range(len(pb) - 2, -1, -1):

            if pb[i] == pb[-1]:
                streak += 1
            else:
                break

        if streak >= 5:

            opposite = "P" if pb[-1] == "B" else "B"

            score[opposite] += 2

            reason.append(f"{pb[-1]} {streak}연속 → 반전")

        ################################################
        # Ping Pong
        ################################################

        if len(pb) >= 6:

            last6 = pb[-6:]

            if last6 == ["P", "B", "P", "B", "P", "B"]:

                score["P"] += 1
                reason.append("PingPong")

            elif last6 == ["B", "P", "B", "P", "B", "P"]:

                score["B"] += 1
                reason.append("PingPong")

        ################################################

        prediction = "P"

        if score["B"] > score["P"]:
            prediction = "B"

        total = score["P"] + score["B"]

        confidence = round(
            max(score.values()) / total,
            3
        )

        return {

            "prediction": prediction,

            "confidence": confidence,

            "reason": reason,

            "score": score,

        }