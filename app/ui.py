import streamlit as st
from config import APP_NAME, APP_VERSION


class CasinoUI:
    def setup(self):
        st.set_page_config(
            page_title=APP_NAME,
            layout="wide"
        )

        st.title(f"🔥 {APP_NAME} {APP_VERSION}")

    def buttons(self):
        c1, c2, c3, c4, c5, c6 = st.columns(6)

        with c1:
            player = st.button("🔵 PLAYER", use_container_width=True)

        with c2:
            banker = st.button("🔴 BANKER", use_container_width=True)

        with c3:
            tie = st.button("🟢 TIE", use_container_width=True)

        with c4:
            undo = st.button("↩ UNDO", use_container_width=True)

        with c5:
            reset = st.button("🗑 RESET", use_container_width=True)

        with c6:
            clear = st.button("⚠ 학습 초기화", use_container_width=True)

        return player, banker, tie, undo, reset, clear

    def main_layout(self):
        return st.columns([1.45, 1])

    def section(self, title):
        st.subheader(title)

    def success(self, text):
        st.success(text)

    def warning(self, text):
        st.warning(text)

    def info(self, text):
        st.info(text)

    def write(self, text):
        st.write(text)

    def metric(self, label, value):
        st.metric(label, value)