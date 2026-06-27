"""Mobile-friendly layout helpers — CASINO PRO AI v9 Mobile Pro."""

import html
from typing import Any, Dict, List, Tuple

CLOUD_BACKUP_WARNING = (
    "무료 클라우드 환경에서는 데이터가 초기화될 수 있으니 DB 백업을 자주 하세요."
)
HOME_SCREEN_HINT = (
    "휴대폰 크롬에서 홈 화면에 추가하면 앱처럼 사용할 수 있습니다."
)

MOBILE_CSS = """
.mobile-pro-stack { display: flex; flex-direction: column; gap: 0.45rem; width: 100%; }
@media (max-width: 768px) {
    .block-container { padding: 0.3rem 0.4rem 0.45rem !important; max-width: 100% !important; }
    .dash-title { font-size: 1.15rem; margin-bottom: 0.15rem; }
    .dash-subtitle { font-size: 0.7rem; margin-bottom: 0.35rem; }
    .cloud-warn {
        font-size: 0.74rem; padding: 0.5rem 0.6rem; margin-bottom: 0.4rem;
        border-radius: 10px; background: rgba(120, 53, 15, 0.45);
        border: 1px solid rgba(251, 191, 36, 0.45); color: #fcd34d;
    }
    .sticky-input-wrap {
        position: sticky; top: 0; z-index: 999;
        background: rgba(7, 11, 20, 0.96);
        backdrop-filter: blur(8px);
        padding: 0.25rem 0 0.35rem; margin-bottom: 0.35rem;
        border-bottom: 1px solid rgba(62, 140, 255, 0.2);
    }
    div[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 0.3rem !important; }
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        flex: 1 1 100% !important; width: 100% !important; min-width: 100% !important;
    }
    .sticky-input-wrap div[data-testid="column"] {
        flex: 1 1 31% !important; width: 31% !important; min-width: 31% !important;
    }
    .sticky-input-wrap div[data-testid="column"]:nth-child(4),
    .sticky-input-wrap div[data-testid="column"]:nth-child(5) {
        flex: 1 1 48% !important; width: 48% !important; min-width: 48% !important;
    }
    .perf-row { grid-template-columns: repeat(2, 1fr) !important; gap: 6px; }
    .perf-v7-row { grid-template-columns: repeat(2, 1fr) !important; }
    .derived-row { grid-template-columns: 1fr !important; }
    .dash-card { padding: 0.55rem 0.6rem; margin-bottom: 0.4rem; }
    .road-scroll, .six-scroll, .mini-scroll {
        -webkit-overflow-scrolling: touch; scroll-behavior: smooth;
    }
    div[data-testid="column"] .stButton > button,
    .stDownloadButton > button {
        min-height: 54px !important; font-size: 0.9rem !important;
        padding: 0.65rem 0.35rem !important;
    }
    .learn-table { font-size: 0.76rem; }
    .conf-big { font-size: 1.45rem; }
    .home-hint { font-size: 0.7rem; color: #94a3b8; margin-top: 0.3rem; }
}
@media (max-width: 480px) {
    .sticky-input-wrap div[data-testid="column"] {
        flex: 1 1 100% !important; width: 100% !important; min-width: 100% !important;
    }
    .perf-row, .perf-v7-row { grid-template-columns: 1fr 1fr !important; }
    .chip { width: 26px; height: 26px; font-size: 0.68rem; }
}
"""


def mobile_pro_open() -> str:
    return '<div class="mobile-pro-stack">'


def mobile_pro_close() -> str:
    return '</div>'


def sticky_input_open() -> str:
    return '<div class="sticky-input-wrap">'


def sticky_input_close() -> str:
    return '</div>'


def render_cloud_warning_html() -> str:
    return (
        f'<div class="cloud-warn">⚠️ {html.escape(CLOUD_BACKUP_WARNING)}</div>'
    )


def render_home_hint_html() -> str:
    return f'<div class="home-hint">📱 {html.escape(HOME_SCREEN_HINT)}</div>'


def perf_v7_color(color: str) -> str:
    mapping = {
        "green": "#22c55e",
        "yellow": "#eab308",
        "red": "#ef4444",
        "gray": "#64748b",
    }
    return mapping.get(color, "#64748b")


def render_perf_v7_html(metrics: Dict[str, Any]) -> str:
    color = metrics.get("health_color", "gray")
    border = perf_v7_color(color)
    items: List[Tuple[str, Any, bool]] = [
        ("총 입력 판수", metrics.get("total_input_hands", 0), False),
        ("누적 AI 예측", metrics.get("total_ai_predictions", 0), False),
        ("확정 예측", metrics.get("resolved_predictions", 0), False),
        ("전체 적중률", f"{metrics.get('overall_accuracy', 0)}%", True),
        ("최근 30 적중률", f"{metrics.get('recent_30_accuracy', 0)}%", True),
        ("최근 100 적중률", f"{metrics.get('recent_100_accuracy', 0)}%", True),
        ("현재 연패", metrics.get("current_losing_streak", 0), False),
        ("최대 연패", metrics.get("max_losing_streak", 0), False),
        ("PASS 비율", f"{metrics.get('pass_rate', 0)}%", False),
        ("평균 신뢰도", f"{round((metrics.get('avg_confidence') or 0) * 100, 1)}%", False),
        ("패턴 메모리 수", metrics.get("pattern_memory_count", 0), False),
        ("학습 신호 수", metrics.get("signal_count", 0), False),
    ]
    cells = "".join(
        f'<div class="perf-item"><div class="perf-label">{html.escape(l)}</div>'
        f'<div class="perf-value{" accent" if acc else ""}">{v}</div></div>'
        for l, v, acc in items
    )
    return (
        f'<div class="dash-card" style="border-color:{border};">'
        f'<div class="card-title">📊 성능 대시보드</div>'
        f'<div class="perf-row perf-v7-row">{cells}</div></div>'
    )
