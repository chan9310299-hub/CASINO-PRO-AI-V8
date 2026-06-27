"""V12 cloud DB UI helpers."""

import html
from typing import Any, Dict

from db_config import is_cloud_db_enabled


def render_cloud_storage_banner(connected: bool) -> str:
    if connected:
        return (
            '<div class="cloud-ok-banner">'
            '☁️ 클라우드 DB 연결됨 — 업데이트 후에도 기록이 유지됩니다.'
            '</div>'
        )
    return (
        '<div class="cloud-warn">'
        '⚠️ 현재 로컬 저장 방식입니다. Streamlit 무료 환경에서는 '
        '업데이트/재부팅 시 데이터가 초기화될 수 있습니다.'
        '</div>'
    )


def render_v12_db_status_card(status: Dict[str, Any]) -> str:
    status = status or {}
    cloud = status.get("cloud_connected") or status.get("storage_mode") == "cloud"
    mode = "클라우드 DB" if cloud else "로컬 SQLite"
    cloud_label = "연결됨" if cloud else "연결 안 됨"
    rows = [
        ("저장 방식", mode),
        ("클라우드 저장", cloud_label),
        ("누적 입력 판수", status.get("total_input_hands", 0)),
        ("누적 AI 예측", status.get("total_ai_predictions", 0)),
        ("패턴 메모리 수", status.get("pattern_memory_count", 0)),
        ("마지막 저장 시간", status.get("last_save_time", "—")),
    ]
    mig = status.get("migration_status") or {}
    if mig.get("migrated"):
        rows.append(("마지막 이전", mig.get("last_migration", "—")))
    table = "".join(
        f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>"
        for k, v in rows
    )
    return (
        f'<div class="dash-card v12-db-card">'
        f'<div class="card-title">💾 DB 저장 상태</div>'
        f'<table class="learn-table">{table}</table></div>'
    )


def cloud_migration_available() -> bool:
    return is_cloud_db_enabled()
