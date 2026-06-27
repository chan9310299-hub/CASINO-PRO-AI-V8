"""Database URL detection — CASINO PRO AI v12."""

import os
from typing import Any, Optional


CLOUD_DB_ERROR_MSG = "클라우드 DB 연결 실패 - Secrets의 DATABASE_URL을 확인하세요"


class DatabaseConnectionError(Exception):
    """Raised when cloud DATABASE_URL is configured but connection fails."""


def _secret_get(secrets: Any, *keys: str) -> Optional[str]:
    cur = secrets
    for key in keys:
        try:
            if isinstance(cur, dict):
                cur = cur.get(key)
            else:
                cur = getattr(cur, key, None) or (cur[key] if key in cur else None)
        except Exception:
            return None
        if cur is None:
            return None
    if cur is None:
        return None
    text = str(cur).strip()
    return text or None


def resolve_database_url(force_sqlite: bool = False) -> Optional[str]:
    """Read DATABASE_URL from environment or Streamlit secrets."""
    if force_sqlite:
        return None

    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url

    try:
        import streamlit as st

        secrets = getattr(st, "secrets", None)
        if not secrets:
            return None

        for key in ("DATABASE_URL", "database_url"):
            val = _secret_get(secrets, key)
            if val:
                return val

        for conn_name in ("postgresql", "postgres", "supabase"):
            for field in ("url", "DATABASE_URL", "database_url"):
                val = _secret_get(secrets, "connections", conn_name, field)
                if val:
                    return val

        try:
            if "DATABASE_URL" in secrets:
                val = str(secrets["DATABASE_URL"]).strip()
                if val:
                    return val
        except Exception:
            pass
    except Exception:
        pass

    return None


def get_database_url() -> Optional[str]:
    return resolve_database_url(force_sqlite=False)


def is_cloud_db_enabled() -> bool:
    return bool(get_database_url())
