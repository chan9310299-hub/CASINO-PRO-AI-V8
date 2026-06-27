"""Optional access-code guard for Streamlit Cloud."""

import streamlit as st


def get_configured_access_code() -> str:
    try:
        code = st.secrets.get("ACCESS_CODE", "")
        return str(code).strip() if code else ""
    except Exception:
        return ""


def is_access_granted() -> bool:
    code = get_configured_access_code()
    if not code:
        return True
    return bool(st.session_state.get("access_ok"))


def render_access_gate() -> bool:
    """Return True if user may proceed to the app."""
    code = get_configured_access_code()
    if not code:
        return True
    if st.session_state.get("access_ok"):
        return True

    st.markdown("### CASINO PRO AI — 접근")
    st.caption("접근 코드가 설정되어 있습니다. 계속하려면 입력하세요.")
    entered = st.text_input("접근 코드", type="password", key="access_code_input")
    if st.button("계속", key="access_code_submit", use_container_width=True):
        if entered == code:
            st.session_state.access_ok = True
            st.rerun()
        else:
            st.error("접근 코드가 올바르지 않습니다.")
    return False
