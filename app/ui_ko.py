"""Korean UI labels — CASINO PRO AI v10 모바일 Ultimate."""

from typing import Any, Dict, Optional

APP_DISPLAY_NAME = "CASINO PRO AI"
VERSION_DISPLAY = "v11"
SUBTITLE = "바카라 로드 분석"
APP_LOAD_OK = "✅ 앱 로딩 완료"

SIX_GRID_TITLE = "6매 GRID"
BIG_ROAD_TITLE = "빅 로드"

HOME_LAYOUT_ORDER = (
    "recent_history",
    "input_buttons",
    "ai_prediction",
    "big_road",
    "six_grid",
    "performance_summary",
)

BTN_PLAYER = "플레이어"
BTN_BANKER = "뱅커"
BTN_TIE = "타이"
BTN_UNDO = "되돌리기"
BTN_RESET = "초기화"

AI_PREDICTION_TITLE = "🎯 AI 예측"

EXP_DETAIL = "▼ 상세 AI 분석"
EXP_PERF = "▼ 성능 분석"
EXP_LEARNING = "▼ AI 학습 기록"
EXP_BACKUP = "▼ 백업 / 내보내기 / 가져오기"
EXP_ADVANCED = "▼ 고급 설정"
EXP_V6 = "V6 연패 방지 대시보드"
EXP_PATTERN = "패턴 랭킹"

BTN_BACKUP_NOW = "지금 백업 만들기"
BTN_DOWNLOAD_BACKUP = "최신 DB 백업 다운로드"
BTN_EXPORT_DB = "DB 내보내기"
BTN_EXPORT_CSV_HIST = "기록 CSV 내보내기"
BTN_EXPORT_CSV_PRED = "예측 CSV 내보내기"
BTN_DOWNLOAD_EXPORT = "내보낸 DB 다운로드"
BTN_IMPORT_DB = "DB 가져오기 (확인 필요)"
UPLOAD_LABEL = "DB 파일 가져오기 (.db)"

GRADE_KO = {
    "A": "우수",
    "B": "양호",
    "C": "주의",
    "—": "—",
}

VOTER_LABELS_KO: Dict[str, str] = {
    "trend_ai": "흐름 AI",
    "road_ai": "로드 AI",
    "pattern_ai": "패턴 AI",
    "memory_ai": "기억 AI",
    "risk_ai": "위험 AI",
    "meta_ai": "종합 AI",
    "streak_ai": "연승/연패 AI",
    "chop_ai": "교차 AI",
    "dragon_ai": "드래곤 AI",
    "reversal_ai": "반전 AI",
    "two_side_balance_ai": "균형 AI",
    "road_consensus_ai": "로드 합의",
    "memory_similarity_ai": "유사패턴",
    "risk_filter_ai": "위험 필터",
    "meta_vote_ai": "종합 판단",
    "anti_six_loss_ai": "6연패 방어",
}

FORBIDDEN_MAIN_UI_ENGLISH = (
    "AI Prediction",
    "Expected hit rate",
    "Confidence",
    "Voter Summary",
    "Trend AI",
    "PLAYER",
    "BANKER",
    "Create backup now",
    "Export DB",
    "Import DB",
    "Backup / Export",
    "Advanced settings",
    "Big Road",
    "Medium",
    "High",
    "Low",
    "neutral",
)

RISK_LEVEL_KO = {
    "LOW": "낮음",
    "MEDIUM": "보통",
    "HIGH": "높음",
    "EXTREME": "매우 높음",
    "CRITICAL": "매우 높음",
}

CONFIDENCE_LABEL_KO = {
    "Very High": "매우 높음",
    "High": "높음",
    "Medium": "보통",
    "Low": "낮음",
}


def prediction_label_ko(pred: Optional[str]) -> str:
    if pred == "P":
        return "플레이어"
    if pred == "B":
        return "뱅커"
    return "—"


def vote_label_ko(vote: Optional[str]) -> str:
    if vote == "P":
        return "플레이어"
    if vote == "B":
        return "뱅커"
    if vote in (None, "", "neutral", "—"):
        return "중립"
    return str(vote)


def risk_level_ko(level: Optional[str]) -> str:
    if not level:
        return "낮음"
    return RISK_LEVEL_KO.get(str(level).upper(), str(level))


def confidence_label_ko(confidence: float, english_label: Optional[str] = None) -> str:
    if english_label and english_label in CONFIDENCE_LABEL_KO:
        return CONFIDENCE_LABEL_KO[english_label]
    if confidence >= 0.85:
        return "매우 높음"
    if confidence >= 0.70:
        return "높음"
    if confidence >= 0.50:
        return "보통"
    return "낮음"


def protection_status_ko(
    prot: Dict[str, Any],
    enabled: bool,
    low_confidence: bool = False,
) -> str:
    if not enabled:
        return "보호 꺼짐"
    risk = str(prot.get("risk_level") or prot.get("streak_risk") or "LOW").upper()
    if risk in ("EXTREME", "HIGH"):
        return "위험 구간 — 신뢰도 낮음"
    if low_confidence or risk == "MEDIUM":
        return "저신뢰 구간"
    return "예측 허용"


def protection_mode_on_ko(enabled: bool) -> str:
    return "켜짐" if enabled else "꺼짐"


def voter_label_ko(name: str) -> str:
    return VOTER_LABELS_KO.get(name, name)
