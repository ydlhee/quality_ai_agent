import streamlit as st


def show_case_status(state):
    """Case의 단계별 진행 상태를 표시한다."""
    st.subheader("Case 진행 상태")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.write("① 설계변경 분석")
        st.write("완료" if state["design_change_analyzed"] else "대기")
    with col2:
        st.write("② 검증계획 생성")
        st.write("완료" if state["validation_plan_created"] else "대기")
    with col3:
        st.write("③ 영향범위 추적")
        st.write("완료" if state["impact_traced"] else "대기")
    with col4:
        st.write("④ 품질검증")
        st.write("완료" if state["quality_validated"] else "대기")
    with col5:
        st.write("⑤ 후속조치")
        if state["followup_completed"]:
            st.write("완료")
        elif state["decision"] == "PASS":
            st.write("불필요")
        else:
            st.write("미실행")


def show_result(state):
    """품질검증 결과와 근거를 표 형태로 표시한다."""
    st.subheader("품질검증 결과")
    quality = state["tool_results"].get("quality", {})
    lot_results = quality.get("result", {}).get("lot_results", [])
    if lot_results:
        result_rows = []
        for item in lot_results:
            result_rows.append({
                "Lot": item.get("lot_id", "-"),
                "판정": item.get("decision", "-"),
                "검증 결과": item.get("reason", "-"),
            })
        st.write("Lot별 판정")
        st.dataframe(result_rows, use_container_width=True, hide_index=True)

    missing_items = state.get("missing_items", [])
    st.write("확인 필요 항목")
    if missing_items:
        missing_rows = []
        for item in missing_items:
            missing_rows.append({
                "Lot": item.get("lot_id", "-"),
                "확인 필요 사항": item.get("reason", "-"),
            })
        st.dataframe(missing_rows, use_container_width=True, hide_index=True)
    else:
        st.success("확인이 필요한 누락 항목이 없습니다.")

    evidence = state.get("evidence", [])
    st.write("검증 근거")
    if evidence:
        evidence_rows = []
        document_type_labels = {
            "INSPECTION_REPORT": "검사성적서",
            "MATERIAL_CERTIFICATE": "소재성적서",
            "HEAT_TREATMENT_CERTIFICATE": "열처리성적서",
        }
        for item in evidence:
            role = item.get("role")
            document_type = item.get("document_type")
            if role == "OLD_DRAWING":
                evidence_type = "변경 전 도면"
            elif role == "NEW_DRAWING":
                evidence_type = "변경 후 도면"
            else:
                evidence_type = document_type_labels.get(document_type, document_type or "-")
            evidence_rows.append({
                "근거문서": item.get("file_name", "-"),
                "문서유형": evidence_type,
                "Lot": item.get("lot_id", "-"),
                "검증결과": item.get("result", "-"),
            })
        st.dataframe(evidence_rows, use_container_width=True, hide_index=True)
    else:
        st.write("등록된 검증 근거가 없습니다.")


def show_followup(state):
    """후속조치 결과를 표 형태로 표시한다."""
    st.subheader("후속조치")
    followup = state["tool_results"].get("followup")
    if not followup:
        if state["decision"] == "PASS":
            st.success("PASS Case로 추가 후속조치가 필요하지 않습니다.")
        else:
            st.write("후속조치가 실행되지 않았습니다.")
        return
    actions = followup.get("result", {}).get("actions", [])
    if not actions:
        st.write("필요한 후속조치가 없습니다.")
        return
    action_rows = []
    for item in actions:
        action_rows.append({
            "Lot": item.get("lot_id", "-"),
            "조치": item.get("action", "-"),
            "내용": item.get("description", "-"),
        })
    st.dataframe(action_rows, use_container_width=True, hide_index=True)


def show_agent_trace(state):
    """Agent의 Tool 선택 이유, 판단 출처 및 실행 결과를 표시한다."""
    st.subheader("Agent 의사결정 Trace")
    traces = state.get("agent_trace", [])
    if not traces:
        st.write("Agent 실행 기록이 없습니다.")
        return
    trace_rows = []
    for trace in traces:
        trace_rows.append({
            "단계": trace.get("step", "-"),
            "선택 Tool": trace.get("tool", "-"),
            "판단 출처": trace.get("decision_source", "미기록"),
            "선택 이유": trace.get("reason", "-"),
            "실행 결과": trace.get("result", "-"),
        })
    st.dataframe(trace_rows, use_container_width=True, hide_index=True)


def show_history(state):
    """Agent의 전체 실행 이력을 표시한다."""
    st.subheader("Agent 실행 이력")
    for index, item in enumerate(state["history"], start=1):
        st.write(f"{index}. {item}")
