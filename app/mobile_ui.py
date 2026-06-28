"""Mobile UI — CASINO PRO AI v11 Smart AI Upgrade."""

import html
from typing import Any, Dict, List, Tuple

CLOUD_BACKUP_WARNING = (
    "무료 클라우드 환경에서는 데이터가 초기화될 수 있으니 DB 백업을 자주 하세요."
)
HOME_SCREEN_HINT = (
    "휴대폰 크롬에서 홈 화면에 추가하면 앱처럼 사용할 수 있습니다."
)

# Mobile-safe CSS: never hide .main / .block-container / stAppViewContainer.
MOBILE_CSS = """
@keyframes barGrow { from { width: 0; } to { width: var(--w, 50%); } }
@keyframes fadeIn { from { opacity: 0.4; transform: translateY(4px); } to { opacity: 1; transform: none; } }

.stApp, .main, [data-testid="stAppViewContainer"], .block-container,
[data-testid="stAppViewContainer"] > section.main,
[data-testid="stVerticalBlock"], [data-testid="stVerticalBlockBorderWrapper"],
.mobile-pro-stack, .mobile-pro-stack > div {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    height: auto !important;
    min-height: auto !important;
    max-height: none !important;
    overflow-x: hidden !important;
    overflow-y: visible !important;
    max-width: 100vw !important;
}

.app-load-ok {
    font-size: 0.75rem; color: #86efac; text-align: center;
    padding: 0.35rem 0.5rem; margin-bottom: 0.35rem;
    background: rgba(34, 197, 94, 0.12); border-radius: 8px;
    border: 1px solid rgba(34, 197, 94, 0.3);
}
.mobile-pro-stack {
    display: flex; flex-direction: column; gap: 0.25rem; width: 100%;
    overflow-x: hidden; overflow-y: visible;
}

/* Streamlit chrome only — do not target footer, section.main, or block-container */
#MainMenu, [data-testid="stToolbar"], [data-testid="stToolbarActions"],
.stDeployButton, .stAppDeployButton {
    display: none !important;
}
header[data-testid="stHeader"] {
    background: transparent !important;
    height: auto !important;
    min-height: 0 !important;
}

.input-section, .prediction-section,
.sticky-input-wrap, .sticky-prediction-wrap {
    position: static !important;
    top: auto !important;
    z-index: auto !important;
    background: transparent;
    padding: 0; margin-bottom: 0.15rem;
}

.v10-header {
    background: rgba(16, 24, 40, 0.95); border: 1px solid rgba(62, 140, 255, 0.25);
    border-radius: 14px; padding: 0.55rem 0.65rem; margin-bottom: 0.35rem;
    box-shadow: 0 6px 24px rgba(0,0,0,0.35);
}
.v10-brand { font-size: 1.15rem; font-weight: 800; color: #5ecbff; margin-bottom: 0.25rem; }
.v10-meta { display: flex; flex-wrap: wrap; gap: 0.5rem 0.75rem; font-size: 0.78rem; color: #94a3b8; }
.v10-pred-card { padding: 0.75rem 0.8rem !important; }
.pred-animate { animation: fadeIn 0.35s ease-out; }
.pred-label-sm { font-size: 0.78rem; color: #94a3b8; text-align: center; margin-bottom: 0.15rem; }
.pred-hero-player, .pred-hero-banker {
    font-size: 2.2rem; font-weight: 900; text-align: center; line-height: 1.15;
    margin: 0.15rem 0 0.45rem; letter-spacing: 0.02em;
}
.pred-hero-player { color: #7ec8ff; text-shadow: 0 0 20px rgba(38,137,232,0.45); }
.pred-hero-banker { color: #ff8a9a; text-shadow: 0 0 20px rgba(217,0,24,0.35); }
.pred-stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-bottom: 0.45rem; }
.pred-stat {
    background: rgba(12, 20, 36, 0.9); border-radius: 10px; padding: 0.4rem 0.3rem; text-align: center;
    border: 1px solid rgba(62, 140, 255, 0.15);
}
.pred-stat-k { font-size: 0.62rem; color: #64748b; }
.pred-stat-v { font-size: 0.95rem; font-weight: 800; color: #e2e8f0; }
.bar-label { font-size: 0.72rem; color: #94a3b8; margin: 0.25rem 0 0.12rem; }
.anim-bar-wrap {
    height: 8px; background: rgba(30,41,59,0.9); border-radius: 999px;
    overflow-x: hidden; overflow-y: visible;
}
.anim-bar-wrap.mini { height: 6px; margin-top: 4px; }
.anim-bar {
    height: 100%; border-radius: 999px;
    animation: barGrow 0.6s ease-out forwards;
    transition: width 0.4s ease;
}
.conf-bar { background: linear-gradient(90deg, #3dffa0, #22c55e); }
.prob-p-bar { background: linear-gradient(90deg, #2689e8, #5ecbff); }
.prob-b-bar { background: linear-gradient(90deg, #d90018, #ff6b7a); }
.reason-score-row {
    display: grid; grid-template-columns: 1fr auto; gap: 0.2rem 0.5rem;
    align-items: center; font-size: 0.82rem; color: #cbd5e1; margin-bottom: 0.35rem;
}
.reason-score { font-weight: 800; color: #3dffa0; }
.v11-reasons-title { font-size: 0.72rem; color: #64748b; margin: 0.45rem 0 0.25rem; }
.v11-reason-row { display: flex; justify-content: space-between; align-items: center; font-size: 0.78rem; color: #cbd5e1; margin-top: 0.2rem; }
.v11-reason-label { flex: 1; }
.v11-reason-score { font-weight: 800; color: #3dffa0; margin-left: 0.5rem; }
.similar-pattern-line { font-size: 0.76rem; color: #94a3b8; margin: 0.35rem 0 0.15rem; line-height: 1.35; }
.cloud-error-banner {
    background: rgba(239, 68, 68, 0.14); border: 1px solid rgba(239, 68, 68, 0.45);
    color: #fca5a5; font-size: 0.78rem; text-align: center; padding: 0.4rem 0.5rem;
    border-radius: 10px; margin-bottom: 0.3rem;
}
.cloud-ok-banner {
    background: rgba(34, 197, 94, 0.12); border: 1px solid rgba(34, 197, 94, 0.35);
    color: #86efac; font-size: 0.78rem; text-align: center; padding: 0.4rem 0.5rem;
    border-radius: 10px; margin-bottom: 0.3rem;
}
.v12-db-card { margin-bottom: 0.35rem !important; }
.v10-perf-row { grid-template-columns: repeat(3, 1fr) !important; }

@media (max-width: 768px) {
    .block-container { padding: 0.25rem 0.35rem 1rem !important; }
    .dash-card { padding: 0.55rem 0.6rem !important; margin-bottom: 0.3rem !important; width: 100%; box-sizing: border-box; }
    .card-title { font-size: 0.9rem !important; text-transform: none !important; }
    .mobile-pro-stack div[data-testid="stHorizontalBlock"] {
        flex-direction: column !important; flex-wrap: nowrap !important;
    }
    .mobile-pro-stack div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        flex: 1 1 100% !important; width: 100% !important;
        min-width: 100% !important; max-width: 100% !important;
    }
    div[data-testid="column"] .stButton > button,
    .stDownloadButton > button {
        min-height: 52px !important; font-size: 1rem !important; font-weight: 700 !important;
        border-radius: 12px !important; width: 100% !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        flex: 1 1 100% !important; width: 100% !important; min-width: 0 !important;
    }
    .road-scroll, .six-scroll { max-width: 100%; overflow-x: auto; overflow-y: visible; -webkit-overflow-scrolling: touch; }
    .pred-hero-player, .pred-hero-banker { font-size: 2rem; }
    .v10-perf-row { grid-template-columns: 1fr !important; }
    .pred-stat-grid { grid-template-columns: 1fr !important; }
    .pred-meta-row { grid-template-columns: 1fr !important; }
    .perf-row { grid-template-columns: 1fr !important; }
}
@media (max-width: 480px) {
    div[data-testid="column"] .stButton > button { min-height: 48px !important; }
}
"""


def render_app_load_ok_html() -> str:
    return '<div class="app-load-ok">✅ 앱 로딩 완료</div>'


def mobile_pro_open() -> str:
    return '<div class="mobile-pro-stack">'


def mobile_pro_close() -> str:
    return '</div>'


def input_section_open() -> str:
    return '<div class="input-section">'


def input_section_close() -> str:
    return '</div>'


def prediction_section_open() -> str:
    return '<div class="prediction-section">'


def prediction_section_close() -> str:
    return '</div>'


def sticky_prediction_open() -> str:
    return prediction_section_open()


def sticky_prediction_close() -> str:
    return prediction_section_close()


def sticky_input_open() -> str:
    return input_section_open()


def sticky_input_close() -> str:
    return input_section_close()


def render_cloud_warning_html() -> str:
    return f'<div class="cloud-warn">⚠️ {html.escape(CLOUD_BACKUP_WARNING)}</div>'


def render_home_hint_html() -> str:
    return f'<div class="home-hint">📱 {html.escape(HOME_SCREEN_HINT)}</div>'


def perf_v7_color(name: str) -> str:
    return {"green": "#22c55e", "yellow": "#eab308", "red": "#ef4444", "gray": "#64748b"}.get(
        name, "#64748b"
    )


def render_perf_v7_html(metrics: Dict[str, Any]) -> str:
    from typing import List, Tuple
    color_map = {"green": "#22c55e", "yellow": "#eab308", "red": "#ef4444", "gray": "#64748b"}
    color = metrics.get("health_color", "gray")
    border = color_map.get(color, "#64748b")
    items: List[Tuple[str, Any, bool]] = [
        ("총 입력 판수", metrics.get("total_input_hands", 0), False),
        ("누적 AI 예측", metrics.get("total_ai_predictions", 0), False),
        ("확정 예측", metrics.get("resolved_predictions", 0), False),
        ("전체 적중률", f"{metrics.get('overall_accuracy', 0)}%", True),
        ("최근 30 적중률", f"{metrics.get('recent_30_accuracy', 0)}%", True),
        ("최근 100 적중률", f"{metrics.get('recent_100_accuracy', 0)}%", True),
        ("현재 연패", metrics.get("current_losing_streak", 0), False),
        ("최대 연패", metrics.get("max_losing_streak", 0), False),
        ("저신뢰 비율", f"{metrics.get('pass_rate', 0)}%", False),
        ("평균 신뢰도", f"{round((metrics.get('avg_confidence') or 0) * 100, 1)}%", False),
    ]
    cells = "".join(
        f'<div class="perf-item"><div class="perf-label">{html.escape(l)}</div>'
        f'<div class="perf-value{" accent" if acc else ""}">{v}</div></div>'
        for l, v, acc in items
    )
    return (
        f'<div class="dash-card" style="border-color:{border};">'
        f'<div class="card-title">📊 상세 성능</div>'
        f'<div class="perf-row perf-v7-row">{cells}</div></div>'
    )
