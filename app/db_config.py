"""Database URL detection — CASINO PRO AI v12."""

import os
from typing import Optional


def get_database_url() -> Optional[str]:
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url
    try:
        import streamlit as st

        if hasattr(st, "secrets"):
            secret_url = st.secrets.get("DATABASE_URL", "")
            if secret_url:
                return str(secret_url).strip()
    except Exception:
        pass
    return None


def is_cloud_db_enabled() -> bool:
    return bool(get_database_url())
