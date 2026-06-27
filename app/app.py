import math
import streamlit as st

from config import APP_NAME, VERSION
from database import Database
from bigroad import BigRoadEngine
from roadmap_ai import RoadmapAI
from bigeye import BigEyeRoad
from smallroad import SmallRoad
from cockroach import CockroachRoad


st.set_page_config(page_title=APP_NAME, layout="wide")


def render_circle_road(data, title):
    cols = max(12, math.ceil(len(data) / 6))

    html = f"""
    <style>
    .mini-scroll {{
        width: 100%;
        overflow-x: auto;
        padding-bottom: 8px;
    }}
    .mini-wrap {{
        display: grid;
        grid-template-columns: repeat({cols}, 32px);
        grid-template-rows: repeat(6, 28px);
        background: #d8d8d8;
        padding: 2px;
        border-radius: 6px;
        width: max-content;
        min-width: max-content;
    }}
    .mini-cell {{
        width: 32px;
        height: 28px;
        background: #f2f2f2;
        border: 1px solid #c9c9c9;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .mini-dot {{
        width: 16px;
        height: 16px;
        border-radius: 50%;
        border: 3px solid;
        background: transparent;
    }}
    .red-dot {{ border-color: #d90018; }}
    .blue-dot {{ border-color: #2689e8; }}
    </style>
    <div class="mini-scroll">
    <div class="mini-wrap">
    """

    for row in range(6):
        for col in range(cols):
            idx = col * 6 + row

            if idx < len(data):
                color = data[idx]
                cls = "red-dot" if color == "R" else "blue-dot"
                html += f'<div class="mini-cell"><div class="mini-dot {cls}"></div></div>'
            else:
                html += '<div class="mini-cell"></div>'

    html += "</div></div>"
    st.subheader(title)
    st.markdown(html, unsafe_allow_html=True)


def render_six_grid(history):
    cols = max(7, math.ceil(len(history) / 6))

    html = f"""
    <style>
    .six-scroll {{
        width: 100%;
        overflow-x: auto;
        padding-bottom: 8px;
    }}
    .six-wrap {{
        display: grid;
        grid-template-columns: repeat({cols}, 46px);
        grid-template-rows: repeat(6, 42px);
        background: #d8d8d8;
        width: max-content;
        min-width: max-content;
        padding: 2px;
        border-radius: 6px;
    }}
    .six-cell {{
        width: 46px;
        height: 42px;
        background: #f2f2f2;
        border: 1px solid #c9c9c9;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .ball {{
        width: 30px;
        height: 30px;
        border-radius: 50%;
        color: white;
        font-weight: 800;
        font-size: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .p {{ background: #2689e8; }}
    .b {{ background: #d90018; }}
    .t {{ background: #287a12; }}
    .empty {{
        width: 30px;
        height: 30px;
        border-radius: 50%;
        background: #e6e6e6;
    }}
    </style>
    <div class="six-scroll">
    <div class="six-wrap">
    """

    for row in range(6):
        for col in range(cols):
            idx = col * 6 + row

            if idx < len(history):
                v = history[idx]
                cls = "p" if v == "P" else "b" if v == "B" else "t"
                html += f'<div class="six-cell"><div class="ball {cls}">{v}</div></div>'
            else:
                html += '<div class="six-cell"><div class="empty"></div></div>'

    html += "</div></div>"
    st.markdown(html, unsafe_allow_html=True)


def render_bigroad(road_data):
    max_col = max([x["col"] for x in road_data], default=0)
    cols = max(12, max_col + 1)

    cell_map = {}
    for item in road_data:
        cell_map[(item["row"], item["col"])] = item

    html = f"""
    <style>
    .road-scroll {{
        width: 100%;
        overflow-x: auto;
        padding-bottom: 10px;
    }}
    .road-wrap {{
        display: grid;
        grid-template-columns: repeat({cols}, 46px);
        grid-template-rows: repeat(6, 42px);
        background: #d8d8d8;
        padding: 2px;
        border-radius: 6px;
        width: max-content;
        min-width: max-content;
    }}
    .road-cell {{
        width: 46px;
        height: 42px;
        background: #f2f2f2;
        border: 1px solid #c9c9c9;
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
    }}
    .road-ball {{
        width: 30px;
        height: 30px;
        border-radius: 50%;
        color: white;
        font-weight: 800;
        font-size: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .p {{ background: #2689e8; }}
    .b {{ background: #d90018; }}
    .tie-mark {{
        position: absolute;
        right: 1px;
        bottom: 1px;
        background: #20b85a;
        color: white;
        font-size: 10px;
        font-weight: 800;
        border-radius: 10px;
        padding: 1px 4px;
    }}
    </style>
    <div class="road-scroll">
    <div class="road-wrap">
    """

    for row in range(6):
        for col in range(cols):
            item = cell_map.get((row, col))

            if item:
                v = item["result"]
                cls = "p" if v == "P" else "b"
                ties = item.get("ties", 0)

                html += f'<div class="road-cell"><div class="road-ball {cls}">{v}</div>'

                if ties > 0:
                    html += f'<div class="tie-mark">T{ties}</div>'

                html += "</div>"
            else:
                html += '<div class="road-cell"><div class="empty"></div></div>'

    html += "</div></div>"
    st.markdown(html, unsafe_allow_html=True)


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


db = Database()

st.title(f"🔥 {APP_NAME} {VERSION}")

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    if st.button("🔵 PLAYER", use_container_width=True):
        db.add_result("P")
        st.rerun()

with c2:
    if st.button("🔴 BANKER", use_container_width=True):
        db.add_result("B")
        st.rerun()

with c3:
    if st.button("🟢 TIE", use_container_width=True):
        db.add_result("T")
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

bigeye = BigEyeRoad(bigroad).build()
smallroad = SmallRoad(bigroad).build()
cockroach = CockroachRoad(bigroad).build()

ai_result = RoadmapAI().analyze(
    history,
    bigroad=bigroad,
    bigeye=bigeye,
    smallroad=smallroad,
    cockroach=cockroach
)

pred = ai_result["prediction"]
conf = ai_result["confidence"]
reason = ai_result["reason"]

stats = calculate_stats(history)

left, right = st.columns([1.5, 1])

with left:
    st.subheader("📊 기록")
    st.write(" → ".join(history))

    st.subheader("🎲 6매 GRID")
    render_six_grid(history)

    st.subheader("🧩 BigRoad")
    render_bigroad(bigroad)

    render_circle_road(bigeye, "👁 BigEye Road")
    render_circle_road(smallroad, "🔹 Small Road")
    render_circle_road(cockroach, "🪳 Cockroach Road")

with right:
    st.subheader("🧠 AI 분석")

    if pred is None:
        st.warning("6개 입력 후 7번째부터 예측 시작")
    else:
        st.success(f"예측: {pred} | 신뢰도: {conf}")
        st.info(f"점수: {reason}")

    st.subheader("🔥 성능")
    st.metric("현재 연승", stats["current_win"])
    st.metric("현재 연패", stats["current_lose"])
    st.metric("최대 연승", stats["max_win"])
    st.metric("최대 연패", stats["max_lose"])
    st.metric("맞춘 횟수", stats["correct"])
    st.metric("틀린 횟수", stats["wrong"])
    st.metric("적중률", f"{stats['accuracy']}%")

    st.subheader("💾 저장")
    st.write("SQLite 저장 완료")
    st.write("파일: data/casino_ai.db")