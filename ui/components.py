import streamlit as st

from mail.gmail_sender import (
    send_gmail,
    get_gmail_account_email,
)
from database.mail_case_repository import get_thread_by_case_id
from database.outbound_mail_repository import (
    save_outbound_mail,
    get_outbound_mail,
)
from email.utils import parseaddr


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
    """
    HOLD / REJECT 후속조치,
    Gmail 발송 및 발송상태 영구 복원 UI.
    """

    followup = (state.get("tool_results") or {}).get("followup") or state.get("followup") or {}
    final_decision = state.get("final_decision") or state.get("decision") or "-"
    case_id = state.get("case_id") or "-"

    st.subheader("05 후속조치 · 재검증")

    # ========================================================
    # 최초 요청 메일 발신자
    # → 후속조치 메일 수신자
    # ========================================================

    original_sender = ""

    try:
        mapping = get_thread_by_case_id(
            case_id
        )

        if mapping:
            original_sender = parseaddr(
                mapping.get("sender") or ""
            )[1]

    except Exception:
        original_sender = ""

    # ========================================================
    # 현재 Gmail 인증 계정
    # → 후속조치 메일 발신자
    # ========================================================

    sender_email = ""

    try:
        sender_email = (
            get_gmail_account_email()
            or ""
        )

    except Exception:
        sender_email = ""

    # ========================================================
    # PASS
    # ========================================================

    if final_decision == "PASS":

        st.success(
            "품질검증이 완료되었습니다. "
            "추가 후속조치가 필요하지 않습니다."
        )

        return

    # ========================================================
    # 후속조치 정보 복원
    # ========================================================
    # Agent state의 followup이 비어 있더라도,
    # 이미 Gmail 발송이력이 존재하면 해당 이력을 이용해
    # 후속조치 상태를 복원한다.

    lot_id = (
        followup.get("lot_id")
        or followup.get("lot")
        or "-"
    )

    reason = (
        followup.get("reason")
        or followup.get("issue")
        or "-"
    )

    required_items = (
        followup.get("required_items")
        or followup.get("requested_items")
        or "-"
    )


    # --------------------------------------------------------
    # followup이 비어 있으면
    # Case의 발송이력에서 Lot / 후속조치 유형을 복원한다.
    # --------------------------------------------------------

    restored_sent_record = None

    if not followup:

        try:
            from database.outbound_mail_repository import (
                get_outbound_mails_by_case,
            )

            case_sent_records = (
                get_outbound_mails_by_case(
                    case_id
                )
            )

        except Exception:
            case_sent_records = []


        if case_sent_records:

            # 가장 최근 발송이력 사용
            restored_sent_record = (
                case_sent_records[0]
            )

            lot_id = (
                restored_sent_record.get(
                    "lot_id"
                )
                or "-"
            )

            restored_action = (
                restored_sent_record.get(
                    "action_type"
                )
                or ""
            )

            # 저장된 발송이력을 기준으로
            # 현재 Case의 후속조치 상태 복원
            if restored_action == "HOLD":
                final_decision = "HOLD"

            elif restored_action == "REJECT":
                final_decision = "REJECT"

        else:

            st.info(
                "현재 생성된 후속조치가 없습니다."
            )

            return


    if isinstance(required_items, list):
        required_items = ", ".join(
            str(item)
            for item in required_items
        )

    # ========================================================
    # 공통 후속조치 설정
    # ========================================================

    if final_decision == "HOLD":

        action_type = "HOLD"

        title = "보완자료 요청"

        default_subject = (
            f"[AeroChange 품질검증] "
            f"{case_id} / {lot_id} "
            "보완자료 요청"
        )

        send_button_text = (
            "담당자 승인 및 Gmail 발송"
        )

        approval_text = (
            "메일 내용을 확인했으며 "
            "협력업체에 발송합니다."
        )

        waiting_text = (
            "협력업체 보완자료 회신 대기"
        )

        st.warning(
            "HOLD · 보완자료 요청이 필요합니다."
        )

    elif final_decision == "REJECT":

        action_type = "REJECT"

        title = "SCAR / 시정조치 요청"

        default_subject = (
            f"[AeroChange SCAR] "
            f"{case_id} / {lot_id} "
            "시정조치 요청"
        )

        send_button_text = (
            "담당자 승인 및 SCAR Gmail 발송"
        )

        approval_text = (
            "SCAR 내용을 확인했으며 "
            "협력업체에 발송합니다."
        )

        waiting_text = (
            "협력업체 시정조치 및 "
            "증빙자료 회신 대기"
        )

        st.error(
            "REJECT · 부적합 시정조치가 필요합니다."
        )

    else:

        st.info(
            f"현재 판정: {final_decision}"
        )

        return

    # ========================================================
    # 후속조치 정보
    # ========================================================

    st.markdown(
        f"#### {title}"
    )

    st.write(
        f"**대상 Lot:** {lot_id}"
    )

    st.write(
        f"**확인사항:** {reason}"
    )

    if final_decision == "HOLD":
        st.write(
            f"**요청자료:** {required_items}"
        )

    st.divider()

    # ========================================================
    # DB에서 기존 발송이력 조회
    # ========================================================

    sent_record = None

    try:
        sent_record = get_outbound_mail(
            case_id=case_id,
            lot_id=lot_id,
            action_type=action_type,
        )

    except Exception as error:
        st.warning(
            "발송이력 조회 중 문제가 발생했습니다: "
            f"{error}"
        )

    # ========================================================
    # 이미 발송된 경우
    # ========================================================

    if sent_record:

        st.markdown(
            "#### 메일 발송 정보"
        )

        st.text_input(
            "발신자 · AeroChange 품질관리 담당자",
            value=(
                sent_record.get(
                    "sender_email"
                )
                or sender_email
                or "-"
            ),
            disabled=True,
            key=(
                f"{action_type}_sent_sender_"
                f"{case_id}_{lot_id}"
            ),
        )

        st.text_input(
            "수신자 · 협력업체 담당자",
            value=(
                sent_record.get(
                    "recipient_email"
                )
                or "-"
            ),
            disabled=True,
            key=(
                f"{action_type}_sent_recipient_"
                f"{case_id}_{lot_id}"
            ),
        )

        st.text_input(
            "메일 제목",
            value=(
                sent_record.get("subject")
                or default_subject
            ),
            disabled=True,
            key=(
                f"{action_type}_sent_subject_"
                f"{case_id}_{lot_id}"
            ),
        )

        st.text_area(
            "발송된 메일 본문",
            value=(
                sent_record.get("body")
                or ""
            ),
            height=300,
            disabled=True,
            key=(
                f"{action_type}_sent_body_"
                f"{case_id}_{lot_id}"
            ),
        )

        st.success(
            "✓ Gmail 발송 완료"
        )

        st.info(
            f"현재 상태 · {waiting_text}"
        )

        sent_at = (
            sent_record.get("sent_at")
            or "-"
        )

        message_id = (
            sent_record.get(
                "gmail_message_id"
            )
            or "-"
        )

        thread_id = (
            sent_record.get(
                "gmail_thread_id"
            )
            or "-"
        )

        st.caption(
            f"발송시각: {sent_at} "
            f"· Message ID: {message_id} "
            f"· Thread ID: {thread_id}"
        )

        # 이미 발송했으므로
        # 승인 체크박스와 발송 버튼을 생성하지 않는다.

    # ========================================================
    # 아직 발송하지 않은 경우
    # ========================================================

    else:

        st.markdown(
            "#### 메일 발송 정보"
        )

        st.text_input(
            "발신자 · AeroChange 품질관리 담당자",
            value=sender_email,
            disabled=True,
            key=(
                f"{action_type}_sender_"
                f"{case_id}_{lot_id}"
            ),
        )

        recipient = st.text_input(
            "수신자 · 협력업체 담당자",
            value=original_sender,
            key=(
                f"{action_type}_recipient_"
                f"{case_id}_{lot_id}"
            ),
            help=(
                "최초 설계변경 요청 메일의 "
                "발신자를 자동으로 불러옵니다."
            ),
        )

        subject = st.text_input(
            "메일 제목",
            value=default_subject,
            key=(
                f"{action_type}_subject_"
                f"{case_id}_{lot_id}"
            ),
        )

        action_data = {}
        draft_data = {}
        actions = (followup.get("result") or {}).get("actions") or []

        if actions and isinstance(actions[0], dict):
            action_data = actions[0]

            if final_decision == "HOLD":
                draft_data = action_data.get("request") or {}

            elif final_decision == "REJECT":
                draft_data = action_data.get("scar_draft") or {}

        default_body = (
            draft_data.get("draft_message")
            or followup.get("draft_message")
            or followup.get("message")
            or followup.get("draft")
            or followup.get("email_body")
            or ""
        )

        body = st.text_area(
            "메일 본문",
            value=default_body,
            height=330,
            key=(
                f"{action_type}_body_"
                f"{case_id}_{lot_id}"
            ),
        )

        approved = st.checkbox(
            approval_text,
            key=(
                f"{action_type}_approve_"
                f"{case_id}_{lot_id}"
            ),
        )

        if st.button(
            send_button_text,
            type="primary",
            disabled=not approved,
            key=(
                f"{action_type}_send_"
                f"{case_id}_{lot_id}"
            ),
            use_container_width=True,
        ):

            if not recipient.strip():

                st.error(
                    "수신자 이메일 주소를 "
                    "입력해 주세요."
                )

            else:

                try:

                    sent = send_gmail(
                        to_email=recipient.strip(),
                        subject=subject.strip(),
                        body=body,
                    )

                    # Gmail API가 성공한 경우에만
                    # 영구 발송이력을 저장한다.
                    save_outbound_mail(
                        case_id=case_id,
                        lot_id=lot_id,
                        action_type=action_type,
                        sender_email=sender_email,
                        recipient_email=(
                            recipient.strip()
                        ),
                        subject=subject.strip(),
                        body=body,
                        gmail_message_id=(
                            sent.get("message_id")
                        ),
                        gmail_thread_id=(
                            sent.get("thread_id")
                        ),
                    )

                    st.success(
                        "Gmail 발송 및 "
                        "발송이력 저장이 완료되었습니다."
                    )

                    st.rerun()

                except Exception as error:

                    st.error(
                        "Gmail 발송 중 오류가 "
                        f"발생했습니다: {error}"
                    )

    # ========================================================
    # 재검증 절차
    # ========================================================

    st.divider()

    st.markdown(
        "#### 재검증 절차"
    )

    if final_decision == "HOLD":

        st.write(
            "1. 보완자료 요청 메일 발송"
        )
        st.write(
            "2. 협력업체 보완자료 준비"
        )
        st.write(
            "3. 협력업체 회신 대기"
        )
        st.write(
            "4. 보완자료 수신"
        )
        st.write(
            "5. 기존 Case 자동 연결"
        )
        st.write(
            "6. 보완자료 등록"
        )
        st.write(
            "7. 관련 항목 재검증"
        )
        st.write(
            "8. 최종 판정"
        )

    else:

        st.write(
            "1. SCAR / 시정조치 요청 발송"
        )
        st.write(
            "2. 협력업체 원인분석 및 시정조치"
        )
        st.write(
            "3. 협력업체 회신 대기"
        )
        st.write(
            "4. 수정자료 및 증빙자료 수신"
        )
        st.write(
            "5. 기존 Case 자동 연결"
        )
        st.write(
            "6. 자료 등록"
        )
        st.write(
            "7. 관련 항목 재검증"
        )
        st.write(
            "8. 최종 판정"
        )

def show_history(state):
    """Agent의 전체 실행 이력을 표시한다."""
    st.subheader("Agent 실행 이력")
    for index, item in enumerate(state["history"], start=1):
        st.write(f"{index}. {item}")





