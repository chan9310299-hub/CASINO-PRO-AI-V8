import math
import streamlit as st


class GridRenderer:
    def __init__(self, history):
        self.history = history

    def render(self):
        data = self.history
        cols = max(7, math.ceil(len(data) / 6))

        html = """
        <style>
        .road-wrap {
            display: inline-grid;
            grid-auto-flow: column;
            grid-template-rows: repeat(6, 48px);
            grid-auto-columns: 58px;
            gap: 0px;
            background: #d8d8d8;
            padding: 2px;
            border-radius: 6px;
            overflow-x: auto;
            max-width: 100%;
        }
        .road-cell {
            width: 58px;
            height: 48px;
            background: #f2f2f2;
            border: 1px solid #c9c9c9;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .ball {
            width: 34px;
            height: 34px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 800;
            font-size: 15px;
            box-shadow:
                inset 0 2px 5px rgba(255,255,255,.45),
                inset 0 -3px 5px rgba(0,0,0,.25);
        }
        .p { background: #2689e8; }
        .b { background: #d90018; }
        .t { background: #287a12; }
        .empty {
            width: 34px;
            height: 34px;
            border-radius: 50%;
            background: #e6e6e6;
            box-shadow:
                inset 0 2px 5px rgba(255,255,255,.8),
                inset 0 -2px 4px rgba(0,0,0,.12);
        }
        </style>
        <div class="road-wrap">
        """

        total_cells = cols * 6

        for i in range(total_cells):
            if i < len(data):
                v = data[i]
                cls = "p" if v == "P" else "b" if v == "B" else "t"
                html += f'<div class="road-cell"><div class="ball {cls}">{v}</div></div>'
            else:
                html += '<div class="road-cell"><div class="empty"></div></div>'

        html += "</div>"

        st.markdown(html, unsafe_allow_html=True)