import html
import math
import sys
from pathlib import Path

import streamlit as st

_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from local_config import APP_NAME, EXPORT_DIR, VERSION
from bigroad import BigRoadEngine
from roadmap_ai import RoadmapAI
from bigeye import BigEyeRoad
from smallroad import SmallRoad
from cockroach import CockroachRoad
from ai.adaptive_learning import build_adaptive_weight_map, lookup_pattern_memory
from ai_learning import (
    calculate_learning_stats,
    ensure_prediction_logged,
    process_new_hand,
)

try:
    from backup_manager import backup_database, daily_backup_if_needed, list_backups, restore_backup
except Exception:
    def backup_database(reason="manual"):
        return None

    def daily_backup_if_needed():
        return None

    def list_backups(limit=20):
        return []

    def restore_backup(backup_path):
        return False

try:
    from export_import import export_db_copy, export_history_csv, export_predictions_csv, import_db_safe
except Exception:
    def export_db_copy():
        return EXPORT_DIR / "export_unavailable.db"

    def export_history_csv(db):
        return EXPORT_DIR / "history.csv"

    def export_predictions_csv(db):
        return EXPORT_DIR / "ai_prediction_history.csv"

    def import_db_safe(source, backup_fn):
        return {"ok": False, "error": "export module unavailable"}

try:
    from mobile_ui import MOBILE_CSS, render_perf_v7_html
except Exception:
    MOBILE_CSS = ""

    def render_perf_v7_html(metrics):
        return ""

try:
    from ai.backtest_report import run_backtest_report
except Exception:
    def run_backtest_report(db):
        return {}

try:
    from ai.pattern_ranking import has_enough_pattern_data, rank_patterns
except Exception:
    def has_enough_pattern_data(db, min_patterns=5):
        return False

    def rank_patterns(db, limit=20):
        return []

try:
    from ai.performance_dashboard import build_performance_dashboard
except Exception:
    def build_performance_dashboard(db, history, ai_result=None):
        return {
            "total_input_hands": len(history or []),
            "total_ai_predictions": 0,
            "resolved_predictions": 0,
            "overall_accuracy": 0,
            "recent_30_accuracy": 0,
            "recent_100_accuracy": 0,
            "current_losing_streak": 0,
            "max_losing_streak": 0,
            "pass_rate": 0,
            "avg_confidence": 0,
            "pattern_memory_count": 0,
            "signal_count": 0,
            "health_color": "gray",
        }

try:
    from database import Database
except Exception:
    raise


st.set_page_config(page_title=APP_NAME, layout="wide", initial_sidebar_state="collapsed")


def inject_dashboard_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
.stApp {
    background: linear-gradient(165deg, #070b14 0%, #0d1526 45%, #0a1020 100%);
    color: #e8eef7;
    font-family: 'Inter', sans-serif;
}
.block-container { padding-top: 1rem; padding-bottom: 0.5rem; max-width: 100%; }
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer, .stDeployButton { visibility: hidden; }
.dash-title {
    font-size: 1.55rem; font-weight: 800; margin: 0 0 0.35rem 0;
    background: linear-gradient(90deg, #5ecbff, #3dffa0);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.dash-subtitle { color: #7a8ba8; font-size: 0.78rem; margin-bottom: 0.75rem; }
.dash-card {
    background: rgba(16, 24, 40, 0.92);
    border: 1px solid rgba(62, 140, 255, 0.22);
    border-radius: 14px; padding: 0.75rem 0.85rem; margin-bottom: 0.6rem;
    box-shadow: 0 8px 28px rgba(0, 0, 0, 0.35);
}
.card-title {
    font-size: 0.8rem; font-weight: 700; color: #8eb4ff;
    margin: 0 0 0.5rem 0; letter-spacing: 0.04em; text-transform: uppercase;
}
.chip-row { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 0.45rem; }
.chip {
    width: 28px; height: 28px; border-radius: 50%;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 0.72rem; font-weight: 800; color: #fff;
}
.chip-p { background: #2689e8; box-shadow: 0 0 10px rgba(38,137,232,0.4); }
.chip-b { background: #d90018; box-shadow: 0 0 10px rgba(217,0,24,0.35); }
.chip-t { background: #22c55e; box-shadow: 0 0 10px rgba(34,197,94,0.35); }
.chip-empty { background: #1e293b; color: #64748b; }
.history-meta { font-size: 0.76rem; color: #94a3b8; }
.history-meta span { color: #cbd5e1; font-weight: 600; }
.pred-card {
    border-radius: 12px; padding: 0.75rem; text-align: center;
    font-size: 1.25rem; font-weight: 800; letter-spacing: 0.06em; margin-bottom: 0.5rem;
}
.pred-player {
    background: linear-gradient(135deg, rgba(38,137,232,0.25), rgba(38,137,232,0.08));
    border: 1px solid rgba(38,137,232,0.55); color: #7ec8ff;
}
.pred-banker {
    background: linear-gradient(135deg, rgba(217,0,24,0.25), rgba(217,0,24,0.08));
    border: 1px solid rgba(255,80,100,0.55); color: #ff8a9a;
}
.pred-wait {
    background: rgba(30,41,59,0.8); border: 1px solid rgba(148,163,184,0.3);
    color: #94a3b8; font-size: 0.88rem;
}
.conf-big {
    font-size: 1.85rem; font-weight: 800; color: #3dffa0; text-align: center;
    line-height: 1.1; margin: 0.15rem 0 0.35rem;
}
.conf-label { text-align: center; font-size: 0.7rem; color: #64748b; margin-bottom: 0.5rem; }
.status-box {
    background: rgba(30, 58, 95, 0.55); border: 1px solid rgba(62, 140, 255, 0.35);
    border-radius: 10px; padding: 0.5rem 0.65rem; font-size: 0.76rem; color: #93c5fd;
    margin-bottom: 0.45rem;
}
.reason-box {
    background: rgba(15, 30, 50, 0.7); border: 1px solid rgba(62, 140, 255, 0.2);
    border-radius: 10px; padding: 0.5rem 0.65rem;
}
.reason-box ul { margin: 0; padding-left: 1rem; font-size: 0.72rem; color: #b8c9e0; line-height: 1.4; }
.perf-row { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; }
.perf-item {
    background: rgba(12, 20, 36, 0.9); border: 1px solid rgba(62, 140, 255, 0.18);
    border-radius: 10px; padding: 0.4rem 0.3rem; text-align: center;
}
.perf-label { font-size: 0.6rem; color: #64748b; margin-bottom: 0.1rem; }
.perf-value { font-size: 0.9rem; font-weight: 700; color: #e2e8f0; }
.perf-value.accent { color: #3dffa0; }
.learn-table { width: 100%; border-collapse: collapse; font-size: 0.74rem; }
.learn-table tr { border-bottom: 1px solid rgba(62, 140, 255, 0.12); }
.learn-table td { padding: 0.35rem 0.2rem; color: #cbd5e1; }
.learn-table td:last-child { text-align: right; font-weight: 700; color: #3dffa0; }
.save-ok { color: #3dffa0; font-size: 0.8rem; font-weight: 600; }
.save-path { color: #64748b; font-size: 0.7rem; margin-top: 0.2rem; }
.dash-footer {
    margin-top: 0.45rem; padding: 0.6rem 0.75rem; border-radius: 10px;
    background: rgba(30, 20, 20, 0.55); border: 1px solid rgba(255, 120, 80, 0.25);
    color: #f0a898; font-size: 0.7rem; text-align: center;
}
.derived-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.45rem; margin-bottom: 0.6rem; }
.derived-card {
    background: rgba(12, 20, 36, 0.85); border: 1px solid rgba(62, 140, 255, 0.15);
    border-radius: 10px; padding: 0.4rem 0.45rem; min-width: 0;
}
.derived-title {
    font-size: 0.65rem; font-weight: 700; color: #7a8ba8;
    margin-bottom: 0.3rem; text-transform: uppercase;
}
.road-scroll, .six-scroll, .mini-scroll { width: 100%; overflow-x: auto; overflow-y: hidden; }
.road-wrap, .six-wrap, .mini-wrap {
    display: grid;
    grid-auto-flow: row;
    background: #111827; border: 1px solid rgba(62, 140, 255, 0.2);
    border-radius: 8px; padding: 2px; width: max-content; max-width: 100%;
}
.road-cell, .six-cell, .mini-cell {
    background: #0f172a; border: 1px solid #1e293b;
    display: flex; align-items: center; justify-content: center; position: relative;
    box-sizing: border-box;
}
.road-cell { width: 36px; height: 32px; }
.six-cell { width: 36px; height: 32px; }
.mini-cell { width: 22px; height: 20px; }
.road-ball, .ball {
    width: 24px; height: 24px; border-radius: 50%; color: white;
    font-weight: 800; font-size: 10px;
    display: flex; align-items: center; justify-content: center;
}
.mini-dot { width: 12px; height: 12px; border-radius: 50%; border: 2px solid; background: transparent; }
.p { background: #2689e8; }
.b { background: #d90018; }
.t { background: #22c55e; }
.red-dot { border-color: #ff4d6d; }
.blue-dot { border-color: #38bdf8; }
.empty { width: 24px; height: 24px; border-radius: 50%; background: #1e293b; }
.tie-mark {
    position: absolute; right: 1px; bottom: 1px; background: #22c55e; color: white;
    font-size: 8px; font-weight: 800; border-radius: 6px; padding: 1px 3px;
}
div[data-testid="column"] .stButton > button {
    border-radius: 10px; font-weight: 700; font-size: 0.8rem;
    border: 1px solid rgba(62, 140, 255, 0.35);
    background: linear-gradient(180deg, #152238, #0f1828); color: #dbeafe;
}
div[data-testid="column"] .stButton > button:hover {
    border-color: #3dffa0; color: #3dffa0;
}
.health-green { border-color: #22c55e !important; }
.health-yellow { border-color: #eab308 !important; }
.health-red { border-color: #ef4444 !important; }
.health-gray { border-color: #64748b !important; }
.prot-ok { color: #3dffa0; font-weight: 700; }
.prot-block { color: #f87171; font-weight: 700; }
""" + MOBILE_CSS + """
</style>
""", unsafe_allow_html=True)


def _md(content):
    st.markdown(content, unsafe_allow_html=True)


def render_history_chips(history, limit=24):
    recent = history[-limit:] if history else []
    chips = "".join(
        f'<span class="chip {"chip-p" if v == "P" else "chip-b" if v == "B" else "chip-t"}">{v}</span>'
        for v in recent
    ) or '<span class="chip chip-empty">—</span>'

    _md(
        f'<div class="dash-card"><div class="card-title">📊 최근 기록</div>'
        f'<div class="chip-row">{chips}</div>'
        f'<div class="history-meta"><span>P: {history.count("P")}</span> &nbsp;|&nbsp; '
        f'<span>B: {history.count("B")}</span> &nbsp;|&nbsp; '
        f'<span>T: {history.count("T")}</span> &nbsp;|&nbsp; '
        f'총 <span>{len(history)}</span> 게임</div></div>'
    )


def render_ai_analysis(pred, conf, status, reason, ai_result=None):
    ai_result = ai_result or {}
    prob_p = ai_result.get("probability_p")
    prob_b = ai_result.get("probability_b")
    voters = ai_result.get("voters") or []

    if pred is None:
        pred_block = (
            f'<div class="pred-card pred-wait">'
            f'{html.escape(status or "6개 입력 후 7번째부터 예측 시작")}</div>'
        )
        conf_block = ""
        prob_block = ""
    elif pred == "PASS":
        pred_block = f'<div class="pred-card pred-wait">PASS</div>'
        conf_block = (
            f'<div class="conf-label" style="margin-bottom:0.5rem;">'
            f'{html.escape(status or "통계적으로 신뢰할 수 있는 예측 없음")}</div>'
        )
        prob_block = ""
    else:
        label = "PLAYER" if pred == "P" else "BANKER"
        cls = "pred-player" if pred == "P" else "pred-banker"
        pct = round(conf * 100, 1)
        pred_block = f'<div class="pred-card {cls}">{label}</div>'
        conf_block = (
            f'<div class="conf-big">{pct}%</div>'
            f'<div class="conf-label">신뢰도 CONFIDENCE</div>'
        )
        p_pct = round((prob_p if prob_p is not None else 0.5) * 100, 1)
        b_pct = round((prob_b if prob_b is not None else 0.5) * 100, 1)
        prob_block = (
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:0.45rem;">'
            f'<div style="text-align:center;font-size:0.72rem;color:#7ec8ff;">'
            f'PLAYER {p_pct}%</div>'
            f'<div style="text-align:center;font-size:0.72rem;color:#ff8a9a;">'
            f'BANKER {b_pct}%</div></div>'
        )

    items = "".join(f"<li>{html.escape(str(r))}</li>" for r in reason) or "<li>—</li>"
    status_text = html.escape(status or "분석 대기")

    voter_labels = {
        "trend_ai": "Trend AI",
        "road_ai": "Road AI",
        "pattern_ai": "Pattern AI",
        "memory_ai": "Memory AI",
        "risk_ai": "Risk AI",
        "meta_ai": "Meta AI",
    }
    voter_rows = ""
    for v in voters:
        label = voter_labels.get(v.get("name"), v.get("name", "—"))
        vote = v.get("vote") or "—"
        voter_rows += (
            f'<tr><td>{html.escape(label)}</td>'
            f'<td>{html.escape(str(vote))}</td></tr>'
        )
    voter_table = (
        f'<table class="learn-table" style="margin-top:0.35rem;">{voter_rows}</table>'
        if voter_rows else ""
    )

    voter_section = ""
    if voter_table:
        voter_section = (
            '<div style="font-size:0.65rem;color:#64748b;margin-top:0.35rem;">'
            'Voter Summary</div>' + voter_table
        )

    _md(
        f'<div class="dash-card"><div class="card-title">🧠 AI 분석</div>'
        f'{pred_block}{conf_block}{prob_block}'
        f'<div class="status-box">📌 {status_text}</div>'
        f'<div class="reason-box"><ul>{items}</ul></div>'
        f'{voter_section}</div>'
    )


def render_data_count_card(data_counts):
    data_counts = data_counts or {}
    rows = [
        ("총 입력 판수", data_counts.get("total_input_hands", 0)),
        ("누적 저장 판수", data_counts.get("accumulated_pb_hands", 0)),
        ("누적 AI 예측", data_counts.get("total_ai_predictions", 0)),
        ("확정 AI 예측", data_counts.get("resolved_ai_predictions", 0)),
        ("패턴 메모리 수", data_counts.get("pattern_memory_count", 0)),
        ("학습 신호 수", data_counts.get("signal_count", 0)),
    ]
    table = "".join(f"<tr><td>{html.escape(str(a))}</td><td>{b}</td></tr>" for a, b in rows)
    _md(
        f'<div class="dash-card"><div class="card-title">📦 데이터 누적 현황</div>'
        f'<table class="learn-table">{table}</table></div>'
    )


def render_v6_dashboard(v6):
    v6 = v6 or {}
    rows = [
        ("Current Losing Streak", v6.get("current_losing_streak", 0)),
        ("Average Losing Streak", v6.get("average_losing_streak", 0)),
        ("Maximum Losing Streak", v6.get("maximum_losing_streak", 0)),
        ("PASS Rate", f"{v6.get('pass_rate', 0)}%"),
        ("Safe Prediction Rate", f"{v6.get('safe_prediction_rate', 0)}%"),
        ("Danger Prediction Rate", f"{v6.get('danger_prediction_rate', 0)}%"),
        ("Road Agreement", f"{v6.get('road_agreement_pct', 0)}%"),
        ("Pattern Similarity", f"{v6.get('pattern_similarity_pct', 0)}%"),
        ("Meta AI Score", v6.get("meta_ai_score", 0)),
        ("Risk Level", v6.get("risk_level", "—")),
        ("Prediction Quality", v6.get("prediction_quality", "—")),
        ("Total Hands Stored", v6.get("total_hands_stored", 0)),
        ("Prediction History", v6.get("prediction_history_count", 0)),
        ("Pattern Memory", v6.get("pattern_memory_count", 0)),
        ("Learning Samples", v6.get("learning_samples", 0)),
        ("Resolved Predictions", v6.get("resolved_predictions", 0)),
        ("Pending Predictions", v6.get("pending_predictions", 0)),
        ("Optimization Count", v6.get("optimization_count", 0)),
    ]
    table = "".join(f"<tr><td>{html.escape(str(a))}</td><td>{b}</td></tr>" for a, b in rows)
    bt = v6.get("backtests") or {}
    bt_rows = ""
    for w in ("100", "300", "500", "1000", "3000", "10000"):
        b = bt.get(w, {})
        if b.get("sample_size", 0) > 0:
            bt_rows += (
                f"<tr><td>Recent {w}</td>"
                f"<td>{b.get('accuracy', 0)}% acc · "
                f"pass {b.get('pass_rate', 0)}% · "
                f"max streak {b.get('maximum_losing_streak', 0)}</td></tr>"
            )
    bt_table = f'<table class="learn-table">{bt_rows}</table>' if bt_rows else ""
    return (
        f'<table class="learn-table">{table}</table>'
        f'{"<div style=\"font-size:0.65rem;color:#64748b;margin:0.4rem 0 0.2rem;\">Backtest</div>" + bt_table if bt_table else ""}'
        f'<div style="font-size:0.62rem;color:#64748b;margin-top:0.35rem;">'
        f'통계 분석 전용 — 베팅 조언·승리 보장 없음</div>'
    )


def render_learning_card(learning):
    best = learning.get("best_signal", "—")
    worst = learning.get("worst_signal", "—")
    if best != "—" and learning.get("best_accuracy"):
        best = f"{best} ({learning['best_accuracy']:.0%})"
    if worst != "—" and learning.get("worst_accuracy") is not None:
        worst = f"{worst} ({learning['worst_accuracy']:.0%})"

    rows = [
        ("총 AI 예측", learning["total_predictions"]),
        ("AI 적중", learning["correct"]),
        ("AI 오답", learning["wrong"]),
        ("AI 적중률", f"{learning['overall_accuracy']}%"),
        ("최근 30 적중률", f"{learning['recent_30_accuracy']}%"),
        ("최근 100 적중률", f"{learning['recent_100_accuracy']}%"),
        ("미확정 예측", learning["pending"]),
        ("학습 신호 수", learning.get("signal_count", 0)),
        ("최고 성능 신호", best),
        ("최저 성능 신호", worst),
        ("패턴 메모리 수", learning.get("pattern_memory_count", 0)),
        ("유사패턴 근거", learning.get("pattern_reason", "—")),
    ]
    table = "".join(f"<tr><td>{html.escape(str(a))}</td><td>{b}</td></tr>" for a, b in rows)
    _md(
        f'<div class="dash-card"><div class="card-title">📈 AI 학습 기록</div>'
        f'<table class="learn-table">{table}</table>'
        f'<div style="font-size:0.66rem;color:#64748b;margin-top:0.4rem;">'
        f'패턴 분석 기록용 — 베팅 조언이 아닙니다.</div></div>'
    )


def render_db_status_card(db_status):
    db_status = db_status or {}
    rows = [
        ("DB 상태", db_status.get("status", "—")),
        ("DB 버전", f"v{db_status.get('version', 0)} / v{db_status.get('target_version', 0)}"),
        ("총 저장 데이터", db_status.get("total_stored_rows", 0)),
        ("마지막 백업", db_status.get("last_backup", "—")),
    ]
    table = "".join(f"<tr><td>{html.escape(str(a))}</td><td>{b}</td></tr>" for a, b in rows)
    _md(
        f'<div class="dash-card"><div class="card-title">🗄 DB 상태</div>'
        f'<table class="learn-table">{table}</table></div>'
    )


def render_protection_mode_card(prot, enabled):
    prot = prot or {}
    allowed = prot.get("prediction_allowed", True)
    streak_risk = prot.get("streak_risk", "LOW")
    status_cls = "prot-ok" if allowed else "prot-block"
    status_txt = "예측 허용" if allowed else "예측 차단"
    _md(
        f'<div class="dash-card"><div class="card-title">🛡 6단계 보호 모드</div>'
        f'<table class="learn-table">'
        f'<tr><td>보호 모드</td><td>{"ON" if enabled else "OFF"}</td></tr>'
        f'<tr><td>현재 연패 위험</td><td>{html.escape(str(streak_risk))}</td></tr>'
        f'<tr><td>최소 신뢰도</td><td>{round((prot.get("min_confidence_required") or 0.55) * 100, 0)}%</td></tr>'
        f'<tr><td>상태</td><td class="{status_cls}">{status_txt}</td></tr>'
        f'</table>'
        f'<div style="font-size:0.65rem;color:#64748b;margin-top:0.35rem;">'
        f'통계적 노출 감소용 — 손실 방지를 보장하지 않습니다.</div></div>'
    )


def render_pattern_ranking(db):
    if not has_enough_pattern_data(db):
        _md(
            '<div class="dash-card"><div class="card-title">🏆 패턴 랭킹</div>'
            '<div style="font-size:0.78rem;color:#94a3b8;">패턴 데이터 부족</div></div>'
        )
        return
    patterns = rank_patterns(db, 20)
    rows = ""
    for p in patterns:
        rows += (
            f"<tr><td>{html.escape(p['pattern'][:24])}</td>"
            f"<td>{p['occurrences']}</td>"
            f"<td>{p['next_p_pct']}%</td>"
            f"<td>{p['next_b_pct']}%</td>"
            f"<td>{round(p['confidence'] * 100, 1)}%</td>"
            f"<td>{html.escape(str(p['last_seen']))}</td></tr>"
        )
    _md(
        f'<div class="dash-card"><div class="card-title">🏆 패턴 랭킹 (Top 20)</div>'
        f'<table class="learn-table"><tr>'
        f'<td>패턴</td><td>횟수</td><td>P%</td><td>B%</td><td>신뢰</td><td>최근</td></tr>'
        f'{rows}</table></div>'
    )


def render_backtest_results(results):
    if not results:
        _md(
            '<div class="dash-card"><div class="card-title">📈 백테스트</div>'
            '<div style="font-size:0.78rem;color:#94a3b8;">데이터 부족</div></div>'
        )
        return
    rows = ""
    for w, b in sorted(results.items(), key=lambda x: int(x[0])):
        rows += (
            f"<tr><td>Recent {w}</td>"
            f"<td>{b.get('accuracy', 0)}% · streak {b.get('maximum_losing_streak', 0)} · "
            f"pass {b.get('pass_rate', 0)}% · n={b.get('sample_size', 0)}<br>"
            f"<span style='color:#64748b;font-size:0.65rem;'>"
            f"best: {html.escape(str(b.get('best_signal', '—')))} · "
            f"worst: {html.escape(str(b.get('worst_signal', '—')))}</span></td></tr>"
        )
    _md(
        f'<div class="dash-card"><div class="card-title">📈 AI 백테스트 결과</div>'
        f'<table class="learn-table">{rows}</table></div>'
    )


def render_data_management(db):
    if "confirm_restore" not in st.session_state:
        st.session_state.confirm_restore = False
    if "confirm_import" not in st.session_state:
        st.session_state.confirm_import = False

    c1, c2 = st.columns(2)
    with c1:
        if st.button("DB 백업", key="btn_db_backup", use_container_width=True):
            path = backup_database("manual")
            if path:
                st.success(f"백업 완료: {path.name}")
            else:
                st.warning("백업할 DB 없음")
    with c2:
        if st.button("최근 백업 복원", key="btn_restore_prompt", use_container_width=True):
            st.session_state.confirm_restore = True

    if st.session_state.confirm_restore:
        backups = list_backups(5)
        if not backups:
            st.info("복원할 백업 없음")
            st.session_state.confirm_restore = False
        else:
            st.warning("현재 DB는 복원 전 자동 백업됩니다. 계속하시겠습니까?")
            choice = st.selectbox("백업 선택", [b.name for b in backups], key="restore_pick")
            c_ok, c_no = st.columns(2)
            with c_ok:
                if st.button("복원 확인", key="btn_restore_ok", use_container_width=True):
                    target = next(b for b in backups if b.name == choice)
                    restore_backup(target)
                    st.session_state.confirm_restore = False
                    st.rerun()
            with c_no:
                if st.button("취소", key="btn_restore_cancel", use_container_width=True):
                    st.session_state.confirm_restore = False
                    st.rerun()

    st.markdown("---")
    ec1, ec2, ec3 = st.columns(3)
    with ec1:
        if st.button("Export DB", key="btn_export_db", use_container_width=True):
            p = export_db_copy()
            st.success(f"Exported: {p.name}")
    with ec2:
        if st.button("Export CSV history", key="btn_export_hist", use_container_width=True):
            p = export_history_csv(db)
            st.success(f"Exported: {p.name}")
    with ec3:
        if st.button("Export CSV predictions", key="btn_export_pred", use_container_width=True):
            p = export_predictions_csv(db)
            st.success(f"Exported: {p.name}")

    uploaded = st.file_uploader("Import DB (.db)", type=["db"], key="import_db_file")
    if uploaded is not None:
        if st.button("Import DB (확인 필요)", key="btn_import_prompt", use_container_width=True):
            st.session_state.confirm_import = True
        if st.session_state.confirm_import:
            st.warning("기존 DB는 import 전 자동 백업됩니다. 덮어쓰시겠습니까?")
            ic1, ic2 = st.columns(2)
            with ic1:
                if st.button("Import 확인", key="btn_import_ok", use_container_width=True):
                    tmp = EXPORT_DIR / uploaded.name
                    tmp.write_bytes(uploaded.getvalue())
                    import_db_safe(tmp, backup_database)
                    st.session_state.confirm_import = False
                    st.rerun()
            with ic2:
                if st.button("Import 취소", key="btn_import_cancel", use_container_width=True):
                    st.session_state.confirm_import = False
                    st.rerun()


def render_learning_reset(db):
    if "confirm_reset_learning" not in st.session_state:
        st.session_state.confirm_reset_learning = False

    if st.button("AI 학습 초기화", key="btn_reset_learning", use_container_width=True):
        st.session_state.confirm_reset_learning = True

    if st.session_state.confirm_reset_learning:
        st.warning("신호 가중치와 패턴 메모리만 초기화합니다. 손 기록과 예측 이력은 유지됩니다.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("확인", key="btn_reset_learning_ok", use_container_width=True):
                db.reset_ai_learning()
                st.session_state.confirm_reset_learning = False
                st.rerun()
        with c2:
            if st.button("취소", key="btn_reset_learning_cancel", use_container_width=True):
                st.session_state.confirm_reset_learning = False
                st.rerun()


def render_performance_card(stats):
    items = [
        ("현재 연승", stats["current_win"], False),
        ("현재 연패", stats["current_lose"], False),
        ("최대 연승", stats["max_win"], False),
        ("최대 연패", stats["max_lose"], False),
        ("맞춘 횟수", stats["correct"], False),
        ("틀린 횟수", stats["wrong"], False),
        ("적중률", f"{stats['accuracy']}%", True),
    ]
    cells = "".join(
        f'<div class="perf-item"><div class="perf-label">{html.escape(l)}</div>'
        f'<div class="perf-value{" accent" if acc else ""}">{v}</div></div>'
        for l, v, acc in items
    )
    _md(
        f'<div class="dash-card"><div class="card-title">🔥 성능 요약</div>'
        f'<div class="perf-row">{cells}</div></div>'
    )


def render_save_card():
    _md(
        '<div class="dash-card"><div class="card-title">💾 저장</div>'
        '<div class="save-ok">● SQLite 저장 완료</div>'
        '<div class="save-path">data/casino_ai.db</div></div>'
    )


def render_footer():
    _md(
        '<div class="dash-footer">'
        '본 프로그램은 분석 및 기록용 도구이며, 어떤 형태의 베팅 조언이나 수익 보장을 하지 않습니다.'
        '</div>'
    )


def render_six_grid(history):
    cols = max(7, math.ceil(len(history) / 6)) if history else 7
    cells = []
    for row in range(6):
        for col in range(cols):
            idx = col * 6 + row
            if idx < len(history):
                v = history[idx]
                cls = "p" if v == "P" else "b" if v == "B" else "t"
                cells.append(f'<div class="six-cell"><div class="ball {cls}">{v}</div></div>')
            else:
                cells.append('<div class="six-cell"><div class="empty"></div></div>')

    _md(
        f'<div class="dash-card"><div class="card-title">🎲 6매 GRID</div>'
        f'<div class="six-scroll"><div class="six-wrap" '
        f'style="grid-template-columns:repeat({cols},36px);grid-template-rows:repeat(6,32px);">'
        f'{"".join(cells)}</div></div></div>'
    )


def render_bigroad(road_data):
    max_col = max((x["col"] for x in road_data), default=0) if road_data else 0
    cols = max(8, max_col + 1)
    cell_map = {(item["row"], item["col"]): item for item in road_data}

    cells = []
    for row in range(6):
        for col in range(cols):
            item = cell_map.get((row, col))
            if not item:
                cells.append('<div class="road-cell"><div class="empty"></div></div>')
                continue
            v = item.get("result")
            ties = item.get("ties", 0)
            if v in ("P", "B"):
                cls = "p" if v == "P" else "b"
                cell = f'<div class="road-cell"><div class="road-ball {cls}">{v}</div>'
                if ties > 0:
                    cell += f'<div class="tie-mark">T{ties}</div>'
                cell += "</div>"
                cells.append(cell)
            elif ties > 0:
                label = f"T{ties}" if ties > 1 else "T"
                cells.append(
                    f'<div class="road-cell"><div class="tie-mark" '
                    f'style="position:static;font-size:9px;padding:2px 5px;">{label}</div></div>'
                )
            else:
                cells.append('<div class="road-cell"></div>')

    _md(
        f'<div class="dash-card"><div class="card-title">🧩 Big Road</div>'
        f'<div class="road-scroll"><div class="road-wrap" '
        f'style="grid-template-columns:repeat({cols},36px);grid-template-rows:repeat(6,32px);">'
        f'{"".join(cells)}</div></div></div>'
    )


def render_derived_row(bigeye_grid, smallroad_grid, cockroach_grid):
    cards = [
        render_circle_road_html_only(bigeye_grid, "👁 BigEye"),
        render_circle_road_html_only(smallroad_grid, "🔹 Small"),
        render_circle_road_html_only(cockroach_grid, "🪳 Cockroach"),
    ]
    _md(f'<div class="derived-row">{"".join(cards)}</div>')


def render_circle_road_html_only(data, title):
    if not data:
        grid = ""
        cols = 6
    elif isinstance(data[0], dict):
        max_col = max(item["col"] for item in data)
        cols = min(max(6, max_col + 1), 14)
        cell_map = {(item["row"], item["col"]): item["mark"] for item in data}
        cells = []
        for row in range(6):
            for col in range(cols):
                mark = cell_map.get((row, col))
                if mark:
                    cls = "red-dot" if mark == "R" else "blue-dot"
                    cells.append(f'<div class="mini-cell"><div class="mini-dot {cls}"></div></div>')
                else:
                    cells.append('<div class="mini-cell"></div>')
        grid = "".join(cells)
    else:
        cols = min(max(6, math.ceil(len(data) / 6)), 14)
        cells = []
        for row in range(6):
            for col in range(cols):
                idx = col * 6 + row
                if idx < len(data):
                    mark = data[idx]
                    cls = "red-dot" if mark == "R" else "blue-dot"
                    cells.append(f'<div class="mini-cell"><div class="mini-dot {cls}"></div></div>')
                else:
                    cells.append('<div class="mini-cell"></div>')
        grid = "".join(cells)

    return (
        f'<div class="derived-card"><div class="derived-title">{html.escape(title)}</div>'
        f'<div class="mini-scroll"><div class="mini-wrap" '
        f'style="grid-template-columns:repeat({cols},22px);grid-template-rows:repeat(6,20px);">'
        f'{grid}</div></div></div>'
    )


def calculate_stats(history):
    current_win = 0
    current_lose = 0
    max_win = 0
    max_lose = 0
    correct = 0
    wrong = 0
    temp = []

    for r in history:
        if r == "T":
            temp.append(r)
            continue

        temp_road = BigRoadEngine()
        temp_road.load(temp)
        road = temp_road.build()

        pred = RoadmapAI().analyze(temp, bigroad=road)["prediction"]

        if pred is not None:
            if pred == r:
                correct += 1
                current_win += 1
                current_lose = 0
                max_win = max(max_win, current_win)
            else:
                wrong += 1
                current_lose += 1
                current_win = 0
                max_lose = max(max_lose, current_lose)

        temp.append(r)

    total = correct + wrong
    accuracy = round((correct / total) * 100, 2) if total else 0.0

    return {
        "current_win": current_win,
        "current_lose": current_lose,
        "max_win": max_win,
        "max_lose": max_lose,
        "correct": correct,
        "wrong": wrong,
        "accuracy": accuracy,
    }


def run_ai_analysis(history, db=None, protection_mode_enabled=True):
    try:
        road_engine = BigRoadEngine()
        road_engine.load(history or [])
        bigroad = road_engine.build()

        bigeye = BigEyeRoad(history=history or []).build()
        smallroad = SmallRoad(history=history or []).build()
        cockroach = CockroachRoad(history=history or []).build()

        weights = build_adaptive_weight_map(db) if db else None
        pattern_fn = (lambda pb: lookup_pattern_memory(db, pb)) if db else None

        return RoadmapAI(weights=weights, pattern_memory_lookup=pattern_fn, db=db).analyze(
            history or [],
            bigroad=bigroad,
            bigeye=bigeye,
            smallroad=smallroad,
            cockroach=cockroach,
            db=db,
            protection_mode_enabled=protection_mode_enabled,
        )
    except Exception:
        from ai.quality_grade import safe_ai_result
        return safe_ai_result()


# --- App ---

inject_dashboard_css()

if "protection_mode_enabled" not in st.session_state:
    st.session_state.protection_mode_enabled = True
if "backtest_results" not in st.session_state:
    st.session_state.backtest_results = None

try:
    daily_backup_if_needed()
except Exception:
    pass

db = Database()
try:
    db_status = db.get_db_status()
except Exception:
    db_status = {}

_md(
    f'<div class="dash-title">🔥 {html.escape(APP_NAME)}</div>'
    f'<div class="dash-subtitle">{html.escape(VERSION)} · Baccarat Road Dashboard</div>'
)

st.session_state.protection_mode_enabled = st.toggle(
    "6단계 보호 모드",
    value=st.session_state.protection_mode_enabled,
    help="연패 시 예측 빈도를 줄이고 PASS를 늘립니다. 손실 방지를 보장하지 않습니다.",
)

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    if st.button("🔵 PLAYER", use_container_width=True):
        process_new_hand(db, "P", lambda h: run_ai_analysis(
            h, db, st.session_state.protection_mode_enabled))
        st.rerun()

with c2:
    if st.button("🔴 BANKER", use_container_width=True):
        process_new_hand(db, "B", lambda h: run_ai_analysis(
            h, db, st.session_state.protection_mode_enabled))
        st.rerun()

with c3:
    if st.button("🟢 TIE", use_container_width=True):
        process_new_hand(db, "T", lambda h: run_ai_analysis(
            h, db, st.session_state.protection_mode_enabled))
        st.rerun()

with c4:
    if st.button("↩ UNDO", use_container_width=True):
        db.undo_last()
        st.rerun()

with c5:
    if st.button("🗑 RESET", use_container_width=True):
        db.reset_current()
        st.rerun()

history = db.get_results()

road_engine = BigRoadEngine()
road_engine.load(history)
bigroad = road_engine.build()

bigeye_engine = BigEyeRoad(history=history)
smallroad_engine = SmallRoad(history=history)
cockroach_engine = CockroachRoad(history=history)

ai_result = run_ai_analysis(history, db, st.session_state.protection_mode_enabled)
ensure_prediction_logged(db, history, ai_result)

pred = ai_result.get("prediction")
conf = ai_result.get("confidence", 0.0)
reason = ai_result.get("reason_in_korean") or ai_result.get("reason", [])
status = ai_result.get("status", "")
grade = ai_result.get("quality_grade", "—")
prot = ai_result.get("protection_mode") or {}
perf_metrics = build_performance_dashboard(db, history, ai_result)

stats = calculate_stats(history)
learning = calculate_learning_stats(db, ai_result)

left, right = st.columns([7, 3])

with left:
    render_history_chips(history)

    grid_col, big_col = st.columns(2)
    with grid_col:
        render_six_grid(history)
    with big_col:
        render_bigroad(bigroad)

    render_derived_row(
        bigeye_engine.build_grid(),
        smallroad_engine.build_grid(),
        cockroach_engine.build_grid(),
    )

    _md(render_perf_v7_html(perf_metrics))
    render_performance_card(stats)

with right:
    if grade and grade != "—":
        _md(
            f'<div style="text-align:center;font-size:0.72rem;color:#8eb4ff;margin-bottom:0.35rem;">'
            f'품질 등급: <strong>{html.escape(str(grade))}</strong></div>'
        )
    render_ai_analysis(pred, conf, status, reason, ai_result)
    render_protection_mode_card(prot, st.session_state.protection_mode_enabled)
    render_db_status_card(db_status)
    v6 = ai_result.get("v6_dashboard") or {}
    with st.expander("📊 V6 Anti-Streak Dashboard", expanded=False):
        _md(render_v6_dashboard(v6))
    render_data_count_card(ai_result.get("data_counts"))
    with st.expander("🏆 패턴 랭킹", expanded=False):
        render_pattern_ranking(db)
    if st.button("AI 백테스트 실행", key="btn_run_backtest", use_container_width=True):
        st.session_state.backtest_results = run_backtest_report(db)
    if st.session_state.backtest_results:
        with st.expander("📈 백테스트 리포트", expanded=True):
            render_backtest_results(st.session_state.backtest_results)
    render_learning_card(learning)
    render_learning_reset(db)
    with st.expander("💾 백업 / Export / Import", expanded=False):
        render_data_management(db)
    render_save_card()

render_footer()
