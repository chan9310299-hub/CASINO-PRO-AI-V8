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

    st.markdown("### CASINO PRO AI — Access")
    st.caption("Access code is configured. Enter it to continue.")
    entered = st.text_input("Access code", type="password", key="access_code_input")
    if st.button("Continue", key="access_code_submit", use_container_width=True):
        if entered == code:
            st.session_state.access_ok = True
            st.rerun()
        else:
            st.error("Invalid access code.")
    return False
