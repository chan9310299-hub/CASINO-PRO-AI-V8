"""V11 mobile UI render helpers."""

import html
from typing import Any, Dict, List, Optional

from ai.final_prediction import LOW_CONFIDENCE_STATUS
from ai.top_reasons import build_top_analysis_reasons
from ai.v11_confidence import PROTECTION_WARNING
from ui_ko import (
    AI_PREDICTION_TITLE,
    confidence_label_ko,
    prediction_label_ko,
    risk_level_ko,
)


def render_v10_header(quality_grade: str, db_status: Dict[str, Any]) -> str:
    from ui_ko import GRADE_KO

    db_status = db_status or {}
    q = GRADE_KO.get(str(quality_grade), quality_grade if quality_grade != "—" else "—")
    db_ok = db_status.get("status", "—")
    return (
        f'<div class="v10-header">'
        f'<div class="v10-brand">CASINO PRO AI</div>'
        f'<div class="v10-meta">'
        f'<span>버전 v12</span>'
        f'<span>AI 품질: <strong>{html.escape(str(q))}</strong></span>'
        f'<span>DB: <strong>{html.escape(str(db_ok))}</strong></span>'
        f'</div></div>'
    )


def _render_reason_rows(ai_result: Dict[str, Any]) -> str:
    top = build_top_analysis_reasons(ai_result, 5)
    rows = ""
    for item in top:
        score = min(float(item.get("score") or 0), 100)
        rows += (
            f'<div class="v11-reason-row">'
            f'<span class="v11-reason-label">{html.escape(item["label"])}</span>'
            f'<span class="v11-reason-score">{score:.0f}%</span>'
            f'</div>'
            f'<div class="anim-bar-wrap mini"><div class="anim-bar conf-bar" '
            f'style="width:{score:.1f}%"></div></div>'
        )
    return rows


def render_v10_prediction_card(pred, conf, ai_result=None) -> str:
    ai_result = ai_result or {}
    prob_p = ai_result.get("probability_p", 0.5)
    prob_b = ai_result.get("probability_b", 0.5)
    low_conf = ai_result.get("low_confidence", False) or (conf or 0) < 0.60
    conf_ko = confidence_label_ko(conf or 0, ai_result.get("confidence_label"))
    risk_ko = risk_level_ko(ai_result.get("risk_level"))
    expected_hit = ai_result.get("expected_hit_rate")
    p_pct = round(float(prob_p) * 100, 1)
    b_pct = round(float(prob_b) * 100, 1)
    prot_warn = ai_result.get("protection_warning") or ""
    similar = ai_result.get("similar_pattern_summary") or {}

    if pred is None:
        return (
            f'<div class="v10-pred-card dash-card pred-animate">'
            f'<div class="card-title">{AI_PREDICTION_TITLE}</div>'
            f'<div class="pred-hero pred-wait">6개 입력 후 예측 시작</div></div>'
        )

    if pred not in ("P", "B"):
        pred = "P" if p_pct >= b_pct else "B"

    label = prediction_label_ko(pred)
    hero_cls = "pred-hero-player" if pred == "P" else "pred-hero-banker"
    if low_conf:
        hero_cls += " pred-low-conf"

    if expected_hit is None:
        side = prob_p if pred == "P" else prob_b
        expected_hit = round(max(conf or 0, side or 0.5) * 100, 1)

    banners = ""
    if prot_warn or (
        low_conf and ai_result.get("protection_mode", {}).get("risk_level") in ("HIGH", "EXTREME")
    ):
        msg = prot_warn or PROTECTION_WARNING
        banners += f'<div class="risk-zone-banner">⚠️ {html.escape(msg)}</div>'
    elif low_conf:
        banners += f'<div class="low-conf-banner">⚠️ {html.escape(LOW_CONFIDENCE_STATUS)}</div>'

    similar_line = ""
    if similar.get("summary"):
        similar_line = (
            f'<div class="similar-pattern-line">'
            f'🔍 {html.escape(str(similar.get("summary")))}'
            f'</div>'
        )

    reason_rows = _render_reason_rows({**ai_result, "prediction": pred})

    return (
        f'<div class="v10-pred-card dash-card pred-animate">'
        f'<div class="card-title">{AI_PREDICTION_TITLE}</div>'
        f'{banners}'
        f'<div class="pred-label-sm">예측</div>'
        f'<div class="{hero_cls}">{html.escape(label)}</div>'
        f'<div class="pred-stat-grid">'
        f'<div class="pred-stat"><div class="pred-stat-k">예상 적중률</div>'
        f'<div class="pred-stat-v">{expected_hit}%</div></div>'
        f'<div class="pred-stat"><div class="pred-stat-k">신뢰도</div>'
        f'<div class="pred-stat-v">{html.escape(conf_ko)}</div></div>'
        f'<div class="pred-stat"><div class="pred-stat-k">위험도</div>'
        f'<div class="pred-stat-v">{html.escape(risk_ko)}</div></div>'
        f'</div>'
        f'<div class="bar-label">신뢰도</div>'
        f'<div class="anim-bar-wrap"><div class="anim-bar conf-bar" style="width:{min(conf or 0, 1)*100:.1f}%"></div></div>'
        f'<div class="bar-label">플레이어 확률 {p_pct}%</div>'
        f'<div class="anim-bar-wrap"><div class="anim-bar prob-p-bar" style="width:{p_pct}%"></div></div>'
        f'<div class="bar-label">뱅커 확률 {b_pct}%</div>'
        f'<div class="anim-bar-wrap"><div class="anim-bar prob-b-bar" style="width:{b_pct}%"></div></div>'
        f'{similar_line}'
        f'<div class="v11-reasons-title">분석 근거</div>'
        f'{reason_rows}'
        f'</div>'
    )


def render_v10_home_stats(stats: Dict[str, Any]) -> str:
    stats = stats or {}
    items = [
        ("오늘 적중률", f"{stats.get('today_accuracy', 0)}%"),
        ("최근30 적중률", f"{stats.get('recent_30_accuracy', 0)}%"),
        ("최근100 적중률", f"{stats.get('recent_100_accuracy', 0)}%"),
        ("현재 연승", stats.get("current_win", 0)),
        ("현재 연패", stats.get("current_lose", 0)),
        ("최고 연승", stats.get("max_win", 0)),
        ("최고 연패", stats.get("max_lose", 0)),
        ("누적 예측", stats.get("total_predictions", 0)),
        ("누적 적중", stats.get("total_hits", 0)),
    ]
    cells = "".join(
        f'<div class="perf-item"><div class="perf-label">{html.escape(k)}</div>'
        f'<div class="perf-value">{v}</div></div>'
        for k, v in items
    )
    return (
        f'<div class="dash-card"><div class="card-title">📊 성능 요약</div>'
        f'<div class="perf-row v10-perf-row">{cells}</div></div>'
    )


def render_v10_detail_analysis(ai_result: Dict[str, Any], reasons: List[str]) -> str:
    top = build_top_analysis_reasons(ai_result, 5)
    rows = ""
    for item in top:
        rows += (
            f'<div class="reason-score-row">'
            f'<span>{html.escape(item["label"])}</span>'
            f'<span class="reason-score">{item["score"]}%</span>'
            f'<div class="anim-bar-wrap mini"><div class="anim-bar conf-bar" '
            f'style="width:{min(item["score"], 100)}%"></div></div>'
            f'</div>'
        )
    similar = ai_result.get("similar_pattern_summary") or {}
    similar_html = ""
    if similar.get("summary"):
        similar_html = (
            f'<div class="similar-pattern-line" style="margin-bottom:0.5rem;">'
            f'🔍 {html.escape(str(similar.get("summary")))}</div>'
        )
    extra = "".join(
        f"<li>{html.escape(str(r))}</li>" for r in (reasons or [])[:5]
    ) or "<li>—</li>"
    return (
        f'<div class="dash-card">'
        f'<div class="card-title">상세 AI 분석</div>'
        f'{similar_html}'
        f'{rows}'
        f'<div class="reason-box" style="margin-top:0.5rem;"><ul>{extra}</ul></div>'
        f'</div>'
    )
