import os

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from agent.runner import run_case
from ui.components import (
    show_case_status,
    show_result,
    show_followup,
    show_history,
)

load_dotenv()

st.set_page_config(
    page_title="AeroChange Trace AI",
    page_icon="✈️",
    layout="wide",
)

# -----------------------------
# Header
# -----------------------------

st.title("AeroChange Trace AI")
st.caption("항공기 설계변경 전주기 품질검증 AI Agent")

st.divider()

# -----------------------------
# Case 실행
# -----------------------------

left, right = st.columns([3, 1])

with left:
    case_id = st.text_input(
        "Case ID",
        value="CASE-001",
        label_visibility="collapsed",
        placeholder="Case ID 입력",
    )

with right:
    run_button = st.button(
        "품질검증 실행",
        use_container_width=True,
        type="primary",
    )

# -----------------------------
# 품질검증 실행
# -----------------------------

if run_button:

    with st.spinner("설계변경 및 품질정보를 검증하고 있습니다..."):
        state = run_case(case_id)

    # Case 요약
    st.subheader(f"Case Overview · {case_id}")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("최종 판정", state["decision"])

    with col2:
        impact = state["tool_results"]["impact"]
        affected_lots = impact["result"]["affected_lots"]
        st.metric("영향 Lot", len(affected_lots))

    with col3:
        missing = state.get("missing_items", [])
        st.metric("확인 필요", len(missing))

    with col4:
        st.metric("실행 Tool", "5 / 5")

    st.divider()

    # Agent 진행상태
    show_case_status(state)

    st.divider()

    # 품질검증 결과
    show_result(state)

    st.divider()

    # 후속조치
    show_followup(state)

    st.divider()

    # Agent 실행 이력
    with st.expander("Agent 실행 이력"):
        show_history(state)