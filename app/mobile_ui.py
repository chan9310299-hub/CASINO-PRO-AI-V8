"""Mobile-friendly layout helpers."""

import html
from typing import Any, Dict, List, Tuple


MOBILE_CSS = """
@media (max-width: 768px) {
    .block-container { padding: 0.45rem 0.5rem !important; max-width: 100% !important; }
    .dash-title { font-size: 1.25rem; }
    .dash-subtitle { font-size: 0.72rem; }
    .perf-row { grid-template-columns: repeat(2, 1fr) !important; gap: 8px; }
    .perf-v7-row { grid-template-columns: repeat(2, 1fr) !important; }
    .derived-row { grid-template-columns: 1fr !important; }
    .dash-card { padding: 0.65rem; margin-bottom: 0.5rem; }
    .road-cell, .six-cell { width: 32px; height: 28px; }
    .mini-cell { width: 20px; height: 18px; }
    div[data-testid="column"] .stButton > button {
        min-height: 46px; font-size: 0.88rem; padding: 0.55rem 0.35rem;
    }
    .learn-table { font-size: 0.78rem; }
    .conf-big { font-size: 1.55rem; }
}
@media (max-width: 480px) {
    .perf-row, .perf-v7-row { grid-template-columns: 1fr 1fr !important; }
    .chip { width: 26px; height: 26px; font-size: 0.68rem; }
}
"""


def mobile_css_block() -> str:
    return f"<style>{MOBILE_CSS}</style>"


def is_mobile_viewport_hint() -> bool:
    return True


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
