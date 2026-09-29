import streamlit as st
from dotenv import load_dotenv

from agent.runner import run_case
from database.live_case_service import create_live_case
from mail.gmail_processor import process_recent_messages
from ui.components import (
    show_case_status,
    show_result,
    show_followup,
    show_history,
)

load_dotenv()


# ============================================================
# Streamlit 설정
# ============================================================

st.set_page_config(
    page_title="AeroChange Trace AI",
    page_icon="✈️",
    layout="wide",
)


# ============================================================
# 공통 결과 화면
# ============================================================

def show_agent_result(state, case_id):
    """
    Agent 실행 결과를 공통 형식으로 표시한다.
    """

    st.subheader(f"Case Overview · {case_id}")

    col1, col2, col3, col4 = st.columns(4)

    # --------------------------------------------------------
    # 최종 판정
    # --------------------------------------------------------

    with col1:
        st.metric(
            "최종 판정",
            state.get("decision", "-"),
        )

    # --------------------------------------------------------
    # 영향 Lot
    # --------------------------------------------------------

    impact = (
        state
        .get("tool_results", {})
        .get("impact", {})
    )

    affected_lots = (
        impact
        .get("result", {})
        .get("affected_lots", [])
    )

    with col2:
        st.metric(
            "영향 Lot",
            len(affected_lots),
        )

    # --------------------------------------------------------
    # 확인 필요 항목
    # --------------------------------------------------------

    missing = state.get(
        "missing_items",
        [],
    )

    with col3:
        st.metric(
            "확인 필요",
            len(missing),
        )

    # --------------------------------------------------------
    # 실행 Tool
    # --------------------------------------------------------

    tool_results = state.get(
        "tool_results",
        {},
    )

    with col4:
        st.metric(
            "실행 Tool",
            len(tool_results),
        )

    st.divider()

    # --------------------------------------------------------
    # Agent 진행상태
    # --------------------------------------------------------

    show_case_status(state)

    st.divider()

    # --------------------------------------------------------
    # 품질검증 결과
    # --------------------------------------------------------

    show_result(state)

    st.divider()

    # --------------------------------------------------------
    # 후속조치
    # --------------------------------------------------------

    show_followup(state)

    st.divider()

    # --------------------------------------------------------
    # Agent 실행 이력
    # --------------------------------------------------------

    with st.expander(
        "Agent 실행 이력"
    ):
        show_history(state)


# ============================================================
# Header
# ============================================================

st.title("AeroChange Trace AI")

st.caption(
    "항공기 설계변경 전주기 품질검증 AI Agent"
)

st.divider()


# ============================================================
# Gmail 수신 메일
# ============================================================

st.subheader("수신 메일")

mail_col1, mail_col2 = st.columns(
    [4, 1]
)

with mail_col1:
    st.write(
        "Gmail에서 AeroChange 관련 메일과 "
        "첨부문서를 확인합니다."
    )

with mail_col2:
    refresh_mail = st.button(
        "메일 새로고침",
        use_container_width=True,
    )


# ============================================================
# Gmail 조회
# ============================================================

if refresh_mail:

    with st.spinner(
        "Gmail 메일과 첨부문서를 확인하고 있습니다..."
    ):

        try:

            mail_results = process_recent_messages(
                max_results=10
            )

            st.session_state[
                "mail_results"
            ] = mail_results

        except Exception as error:

            st.error(
                f"Gmail 조회 중 오류가 발생했습니다: {error}"
            )


# ============================================================
# 메일 목록
# ============================================================

mail_results = st.session_state.get(
    "mail_results",
    [],
)


if not mail_results:

    st.info(
        "메일 새로고침을 누르면 "
        "AeroChange 관련 메일을 조회합니다."
    )


else:

    for index, mail in enumerate(
        mail_results,
        start=1,
    ):

        subject = mail.get(
            "subject",
            "(제목 없음)",
        )

        mail_type = mail.get(
            "mail_type",
            "UNKNOWN",
        )

        case_id = mail.get(
            "case_id"
        )

        thread_id = mail.get(
            "thread_id"
        )

        parsed_documents = mail.get(
            "parsed_documents",
            [],
        )

        # ----------------------------------------------------
        # 메일 역할 표시
        # ----------------------------------------------------

        if mail_type == "NEW":
            mail_role = "신규 Case"

        elif mail_type == "SUPPLEMENTAL":
            mail_role = "보완 / 후속 자료"

        else:
            mail_role = mail_type

        # ----------------------------------------------------
        # 메일 Expander
        # ----------------------------------------------------

        with st.expander(
            f"{index}. {subject}"
        ):

            col1, col2, col3 = st.columns(3)

            with col1:

                st.write("**발신자**")

                st.write(
                    mail.get(
                        "from",
                        "-"
                    )
                )

            with col2:

                st.write("**메일 역할**")

                st.write(mail_role)

            with col3:

                st.write("**연결 Case**")

                st.write(
                    case_id
                    if case_id
                    else "-"
                )

            # ------------------------------------------------
            # 분류 사유
            # ------------------------------------------------

            st.write("**분류 사유**")

            st.write(
                mail.get(
                    "reason",
                    "-"
                )
            )

            # ------------------------------------------------
            # Gmail Thread
            # ------------------------------------------------

            with st.expander(
                "메일 상세정보"
            ):

                st.write("**Gmail Thread ID**")

                st.code(
                    thread_id
                    if thread_id
                    else "-"
                )

                st.write("**본문**")

                body = mail.get(
                    "body",
                    ""
                )

                st.text(
                    body
                    if body
                    else "(본문 없음)"
                )

            # ------------------------------------------------
            # 첨부문서 분석
            # ------------------------------------------------

            st.write("**첨부문서 분석**")

            if not parsed_documents:

                st.warning(
                    "분석 가능한 첨부문서가 없습니다."
                )

            else:

                success_count = sum(
                    1
                    for document in parsed_documents
                    if document.get("parse_status")
                    in {
                        "SUCCESS",
                        "WARNING",
                    }
                )

                st.write(
                    f"첨부문서 분석 "
                    f"**{success_count}/{len(parsed_documents)} 완료**"
                )

                for document in parsed_documents:

                    document_type = document.get(
                        "document_type",
                        "UNKNOWN",
                    )

                    parse_status = document.get(
                        "parse_status",
                        "UNKNOWN",
                    )

                    file_name = document.get(
                        "file_name",
                        "-",
                    )

                    if parse_status == "SUCCESS":
                        status_icon = "✓"

                    elif parse_status == "WARNING":
                        status_icon = "⚠"

                    else:
                        status_icon = "✕"

                    st.write(
                        f"{status_icon} "
                        f"{file_name} "
                        f"· {document_type} "
                        f"· {parse_status}"
                    )

                # --------------------------------------------
                # 구조화 데이터는 개발/상세정보로 숨김
                # --------------------------------------------

                with st.expander(
                    "상세 분석정보"
                ):

                    for document in parsed_documents:

                        st.markdown(
                            f"**{document.get('file_name', '-')}**"
                        )

                        st.write(
                            "문서 유형:",
                            document.get(
                                "document_type",
                                "UNKNOWN",
                            )
                        )

                        st.write(
                            "Parser 상태:",
                            document.get(
                                "parse_status",
                                "UNKNOWN",
                            )
                        )

                        if document.get(
                            "parse_status"
                        ) in {
                            "SUCCESS",
                            "WARNING",
                        }:

                            st.json(
                                document.get(
                                    "structured_data",
                                    {}
                                )
                            )

                        elif document.get(
                            "parse_status"
                        ) == "ERROR":

                            st.error(
                                document.get(
                                    "error",
                                    "Parser 오류",
                                )
                            )

                        st.divider()

            # =================================================
            # 신규 Case 생성 + Agent 검증
            # =================================================

            if mail_type == "NEW":

                st.divider()

                st.write(
                    "**처리 상태:** "
                    "Case 생성 대기"
                )

                start_button = st.button(
                    "Case 생성 및 검증 시작",
                    key=f"create_case_{index}_{thread_id}",
                    type="primary",
                    use_container_width=True,
                )

                if start_button:

                    try:

                        # ------------------------------------
                        # 1. Gmail 메일 → Case 생성
                        # ------------------------------------

                        with st.spinner(
                            "메일과 첨부문서를 기반으로 "
                            "Case를 생성하고 있습니다..."
                        ):

                            create_result = (
                                create_live_case(
                                    mail
                                )
                            )

                        if not create_result.get(
                            "success"
                        ):

                            errors = create_result.get(
                                "errors",
                                [],
                            )

                            st.error(
                                "Case를 생성할 수 없습니다."
                            )

                            if errors:

                                for error in errors:
                                    st.write(
                                        f"- {error}"
                                    )

                        else:

                            created_case_id = (
                                create_result.get(
                                    "case_id"
                                )
                            )

                            already_exists = (
                                create_result.get(
                                    "already_exists",
                                    False,
                                )
                            )

                            # --------------------------------
                            # Case 생성 결과
                            # --------------------------------

                            if already_exists:

                                st.info(
                                    f"기존 Case "
                                    f"{created_case_id}와 "
                                    f"연결된 메일입니다."
                                )

                            else:

                                st.success(
                                    f"{created_case_id} "
                                    f"생성이 완료되었습니다."
                                )

                            # --------------------------------
                            # 2. Agent 자동 실행
                            # --------------------------------

                            with st.spinner(
                                f"{created_case_id}의 "
                                f"설계변경 영향과 품질문서를 "
                                f"검증하고 있습니다..."
                            ):

                                state = run_case(
                                    created_case_id
                                )

                            # --------------------------------
                            # 3. 결과 Session 저장
                            # --------------------------------

                            st.session_state[
                                "last_agent_state"
                            ] = state

                            st.session_state[
                                "last_case_id"
                            ] = created_case_id

                            # --------------------------------
                            # 4. 최종 결과 안내
                            # --------------------------------

                            decision = state.get(
                                "decision",
                                "-"
                            )

                            case_status = state.get(
                                "case_status",
                                "-"
                            )

                            if decision == "PASS":

                                st.success(
                                    f"{created_case_id} "
                                    f"품질검증 결과: PASS"
                                )

                            elif decision == "HOLD":

                                st.warning(
                                    f"{created_case_id} "
                                    f"품질검증 결과: HOLD"
                                )

                            elif decision == "REJECT":

                                st.error(
                                    f"{created_case_id} "
                                    f"품질검증 결과: REJECT"
                                )

                            else:

                                st.info(
                                    f"{created_case_id} "
                                    f"검증 결과: {decision}"
                                )

                            st.write(
                                f"**Case 상태:** "
                                f"{case_status}"
                            )

                            st.divider()

                            # --------------------------------
                            # 5. Agent 상세 결과
                            # --------------------------------

                            show_agent_result(
                                state,
                                created_case_id,
                            )

                    except Exception as error:

                        st.error(
                            "Case 생성 또는 Agent 실행 중 "
                            f"오류가 발생했습니다: {error}"
                        )


            # =================================================
            # 이미 Case에 연결된 메일
            # =================================================

            elif mail_type == "SUPPLEMENTAL":

                st.divider()

                st.write(
                    "**처리 상태:** "
                    "기존 Case 연결 메일"
                )

                if case_id:

                    st.info(
                        f"{case_id}에 연결된 "
                        f"보완/후속 자료입니다."
                    )


st.divider()


# ============================================================
# 개발 / 테스트용 Case 직접 실행
# ============================================================

st.subheader(
    "Case 직접 검증"
)

st.caption(
    "개발 및 테스트용 기능입니다. "
    "Case ID를 직접 입력하여 Agent를 실행할 수 있습니다."
)

left, right = st.columns(
    [3, 1]
)

with left:

    manual_case_id = st.text_input(
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
        key="manual_run_case",
    )


# ============================================================
# 직접 Case 실행
# ============================================================

if run_button:

    try:

        with st.spinner(
            "설계변경 및 품질정보를 검증하고 있습니다..."
        ):

            state = run_case(
                manual_case_id
            )

        st.session_state[
            "last_agent_state"
        ] = state

        st.session_state[
            "last_case_id"
        ] = manual_case_id

        show_agent_result(
            state,
            manual_case_id,
        )

    except Exception as error:

        st.error(
            f"Case 실행 중 오류가 발생했습니다: {error}"
        )