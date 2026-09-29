import streamlit as st
from dotenv import load_dotenv

from agent.runner import run_case
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


# ------------------------------------------------------------
# Gmail 조회
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# 메일 목록 표시
# ------------------------------------------------------------

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

        with st.expander(
            f"{index}. {subject} · {mail_type}"
        ):

            col1, col2, col3 = st.columns(
                3
            )

            with col1:

                st.write("**발신자**")

                st.write(
                    mail.get(
                        "from",
                        "-"
                    )
                )

            with col2:

                st.write("**메일 유형**")

                st.write(
                    mail_type
                )

            with col3:

                st.write("**연결 Case**")

                st.write(
                    case_id
                    if case_id
                    else "신규 Case 후보"
                )

            st.write("**분류 사유**")

            st.write(
                mail.get(
                    "reason",
                    "-"
                )
            )

            st.write("**Gmail Thread ID**")

            st.code(
                mail.get(
                    "thread_id",
                    "-"
                )
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

            st.write("**첨부문서 분석**")

            parsed_documents = mail.get(
                "parsed_documents",
                [],
            )

            if not parsed_documents:

                st.write(
                    "첨부문서 없음"
                )

            else:

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
                        "-"
                    )

                    st.markdown(
                        f"**{file_name}**"
                    )

                    doc_col1, doc_col2 = st.columns(
                        2
                    )

                    with doc_col1:

                        st.write(
                            f"문서 유형: `{document_type}`"
                        )

                    with doc_col2:

                        st.write(
                            f"Parser 상태: `{parse_status}`"
                        )

                    if parse_status in {
                        "SUCCESS",
                        "WARNING",
                    }:

                        with st.expander(
                            "구조화 데이터 보기"
                        ):

                            st.json(
                                document.get(
                                    "structured_data",
                                    {}
                                )
                            )

                    elif parse_status == "ERROR":

                        st.error(
                            document.get(
                                "error",
                                "Parser 오류"
                            )
                        )

                    st.divider()


st.divider()


# ============================================================
# Case 직접 실행
# ============================================================

st.subheader("Case 품질검증")

left, right = st.columns(
    [3, 1]
)

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


# ============================================================
# 품질검증 실행
# ============================================================

if run_button:

    try:

        with st.spinner(
            "설계변경 및 품질정보를 검증하고 있습니다..."
        ):

            state = run_case(
                case_id
            )

        # ----------------------------------------------------
        # Case Overview
        # ----------------------------------------------------

        st.subheader(
            f"Case Overview · {case_id}"
        )

        col1, col2, col3, col4 = st.columns(
            4
        )

        with col1:

            st.metric(
                "최종 판정",
                state.get(
                    "decision",
                    "-"
                )
            )

        with col2:

            impact = state.get(
                "tool_results",
                {}
            ).get(
                "impact",
                {}
            )

            affected_lots = impact.get(
                "result",
                {}
            ).get(
                "affected_lots",
                []
            )

            st.metric(
                "영향 Lot",
                len(affected_lots)
            )

        with col3:

            missing = state.get(
                "missing_items",
                []
            )

            st.metric(
                "확인 필요",
                len(missing)
            )

        with col4:

            tool_results = state.get(
                "tool_results",
                {}
            )

            st.metric(
                "실행 Tool",
                len(tool_results)
            )

        st.divider()

        # ----------------------------------------------------
        # Agent 진행상태
        # ----------------------------------------------------

        show_case_status(
            state
        )

        st.divider()

        # ----------------------------------------------------
        # 품질검증 결과
        # ----------------------------------------------------

        show_result(
            state
        )

        st.divider()

        # ----------------------------------------------------
        # 후속조치
        # ----------------------------------------------------

        show_followup(
            state
        )

        st.divider()

        # ----------------------------------------------------
        # Agent 실행 이력
        # ----------------------------------------------------

        with st.expander(
            "Agent 실행 이력"
        ):

            show_history(
                state
            )

    except Exception as error:

        st.error(
            f"Case 실행 중 오류가 발생했습니다: {error}"
        )