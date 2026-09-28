import streamlit as st


def show_case_status(state):
    """Case의 단계별 진행 상태를 표시한다."""

    st.subheader("Case 진행 상태")

    st.write(
        "설계변경 분석:",
        "완료" if state["design_change_analyzed"] else "대기"
    )

    st.write(
        "검증계획 생성:",
        "완료" if state["validation_plan_created"] else "대기"
    )

    st.write(
        "영향범위 추적:",
        "완료" if state["impact_traced"] else "대기"
    )

    st.write(
        "품질검증:",
        "완료" if state["quality_validated"] else "대기"
    )

    st.write(
        "후속조치·재검증:",
        "완료" if state["followup_completed"] else "대기"
    )


def show_result(state):
    """품질검증 결과와 근거를 표시한다."""

    st.subheader("품질검증 결과")

    st.write("최종 판정:", state["decision"])

    st.write("누락 항목")
    st.write(state["missing_items"])

    st.write("Evidence")
    st.write(state["evidence"])


def show_followup(state):
    """후속조치 및 재검증 상태를 표시한다."""

    st.subheader("후속조치 및 재검증")

    followup = state["tool_results"].get("followup")

    if not followup:
        st.write("후속조치가 없습니다.")
        return

    st.write("조치:", followup["action"])
    st.write("대상:", followup["target"])
    st.write("요청자료:", followup["requested_document"])
    st.write("재검증 상태:", followup["revalidation_status"])


def show_history(state):
    """Agent의 Tool 실행 이력을 표시한다."""

    st.subheader("Agent 실행 이력")

    for index, item in enumerate(state["history"], start=1):
        st.write(f"{index}. {item}")