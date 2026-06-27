from datetime import datetime


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_result(value):
    if value in ("P", "B", "T"):
        return value
    return None


def result_name(value):
    if value == "P":
        return "PLAYER"
    if value == "B":
        return "BANKER"
    if value == "T":
        return "TIE"
    return "-"