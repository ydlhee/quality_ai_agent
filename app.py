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
# 공통 함수
# ============================================================

DOCUMENT_TYPE_LABELS = {
    "DRAWING": "도면",
    "INSPECTION_REPORT": "검사성적서",
    "MATERIAL_CERTIFICATE": "소재성적서",
    "HEAT_TREATMENT_CERTIFICATE": "열처리성적서",
}


def safe_value(data, key, default="-"):
    value = data.get(key)

    if value is None or value == "":
        return default

    return value


def format_number(value, digits=2):
    if value is None:
        return "-"

    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def get_characteristic(data):
    """
    도면/검사성적서에서 첫 번째 주요 치수 정보를 가져온다.
    Parser 구조가 약간 달라도 최대한 대응한다.
    """

    characteristics = data.get("characteristics", [])

    if characteristics:
        return characteristics[0]

    measurements = data.get("measurements", [])

    if measurements:
        return measurements[0]

    inspection_results = data.get("inspection_results", [])

    if inspection_results:
        return inspection_results[0]

    return {}


def get_tolerance(characteristic, data=None):
    data = data or {}

    tolerance = characteristic.get("tolerance")

    if tolerance is None:
        tolerance = characteristic.get("tolerance_mm")

    if tolerance is None:
        tolerance = data.get("tolerance")

    if tolerance is None:
        tolerance = data.get("tolerance_mm")

    return tolerance


def get_nominal(characteristic, data=None):
    data = data or {}

    nominal = characteristic.get("nominal")

    if nominal is None:
        nominal = characteristic.get("nominal_mm")

    if nominal is None:
        nominal = data.get("nominal")

    if nominal is None:
        nominal = data.get("nominal_mm")

    return nominal


def get_measured(characteristic, data=None):
    data = data or {}

    measured = characteristic.get("measured")

    if measured is None:
        measured = characteristic.get("measured_mm")

    if measured is None:
        measured = characteristic.get("actual")

    if measured is None:
        measured = data.get("measured")

    if measured is None:
        measured = data.get("measured_mm")

    return measured


# ============================================================
# 도면 요약
# ============================================================

def show_drawing_summary(document, drawing_role=None):
    data = document.get("structured_data") or {}

    revision = safe_value(data, "revision")
    drawing_no = safe_value(data, "drawing_no")
    part_no = safe_value(data, "part_no")
    effective_from = safe_value(data, "effective_from")
    material = safe_value(data, "material")
    heat_treatment = safe_value(data, "heat_treatment")

    characteristic = get_characteristic(data)

    characteristic_name = (
        characteristic.get("name")
        or characteristic.get("characteristic_name")
        or characteristic.get("description")
        or characteristic.get("characteristic_id")
        or "주요 치수"
    )

    nominal = get_nominal(characteristic, data)
    tolerance = get_tolerance(characteristic, data)

    if drawing_role:
        title = f"{drawing_role} · Rev.{revision}"
    else:
        title = f"도면 · Rev.{revision}"

    st.markdown(f"#### {title}")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.write(f"**도면번호**  \n{drawing_no}")
        st.write(f"**부품번호**  \n{part_no}")

    with col2:
        st.write(f"**적용일**  \n{effective_from}")
        st.write(f"**재질**  \n{material}")

    with col3:
        st.write(f"**열처리**  \n{heat_treatment}")

        if nominal != "-" and tolerance != "-":
            st.write(
                f"**주요 치수**  \n"
                f"{characteristic_name} "
                f"{format_number(nominal)} ± "
                f"{format_number(tolerance)} mm"
            )
        else:
            st.write(f"**주요 치수**  \n{characteristic_name}")


# ============================================================
# 검사성적서 요약
# ============================================================

def show_inspection_summary(document):
    data = document.get("structured_data") or {}

    lot_no = (
        data.get("lot_no")
        or data.get("lot_id")
        or "-"
    )

    revision = safe_value(data, "revision")

    characteristic = get_characteristic(data)

    nominal = get_nominal(characteristic, data)
    tolerance = get_tolerance(characteristic, data)
    measured = get_measured(characteristic, data)

    st.markdown("#### 검사성적서")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.write(f"**대상 Lot**  \n{lot_no}")
        st.write(f"**적용 Revision**  \n{revision}")

    with col2:
        st.write(
            f"**요구치**  \n"
            f"{format_number(nominal)} ± "
            f"{format_number(tolerance)} mm"
        )

        st.write(
            f"**측정값**  \n"
            f"{format_number(measured)} mm"
        )

    with col3:
        try:
            lower = float(nominal) - float(tolerance)
            upper = float(nominal) + float(tolerance)

            st.write(
                f"**허용범위**  \n"
                f"{lower:.2f} ~ {upper:.2f} mm"
            )

            if measured is not None:
                measured_float = float(measured)

                if lower <= measured_float <= upper:
                    st.success("허용공차 내")
                else:
                    st.error("허용공차 초과")

        except (TypeError, ValueError):
            st.write("**허용범위**  \n-")


# ============================================================
# 소재/열처리 성적서 요약
# ============================================================

def show_certificate_summary(document):
    data = document.get("structured_data") or {}
    document_type = document.get("document_type")

    lot_no = (
        data.get("lot_no")
        or data.get("lot_id")
        or "-"
    )

    material = safe_value(data, "material")
    heat_treatment = safe_value(data, "heat_treatment")

    heat_no = (
        data.get("heat_no")
        or data.get("heat_number")
        or "-"
    )

    supplier = (
        data.get("supplier_id")
        or data.get("supplier")
        or "-"
    )

    if document_type == "MATERIAL_CERTIFICATE":
        title = "소재성적서"
    else:
        title = "열처리성적서"

    st.markdown(f"#### {title}")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.write(f"**대상 Lot**  \n{lot_no}")
        st.write(f"**협력업체**  \n{supplier}")

    with col2:
        st.write(f"**재질**  \n{material}")

        if document_type == "HEAT_TREATMENT_CERTIFICATE":
            st.write(
                f"**열처리 조건**  \n{heat_treatment}"
            )

    with col3:
        st.write(f"**Heat No.**  \n{heat_no}")


# ============================================================
# 주요 설계변경 요약
# ============================================================

def show_design_change_summary(drawings):
    if len(drawings) < 2:
        return

    drawing_data = [
        document.get("structured_data") or {}
        for document in drawings
    ]

    drawing_data = sorted(
        drawing_data,
        key=lambda x: str(x.get("revision", "")),
    )

    old_data = drawing_data[0]
    new_data = drawing_data[-1]

    old_revision = safe_value(old_data, "revision")
    new_revision = safe_value(new_data, "revision")

    old_characteristic = get_characteristic(old_data)
    new_characteristic = get_characteristic(new_data)

    old_nominal = get_nominal(
        old_characteristic,
        old_data,
    )

    new_nominal = get_nominal(
        new_characteristic,
        new_data,
    )

    old_tolerance = get_tolerance(
        old_characteristic,
        old_data,
    )

    new_tolerance = get_tolerance(
        new_characteristic,
        new_data,
    )

    old_material = safe_value(
        old_data,
        "material",
    )

    new_material = safe_value(
        new_data,
        "material",
    )

    old_heat = safe_value(
        old_data,
        "heat_treatment",
    )

    new_heat = safe_value(
        new_data,
        "heat_treatment",
    )

    changes = []

    if old_nominal != new_nominal:
        changes.append(
            f"치수: {format_number(old_nominal)} mm "
            f"→ {format_number(new_nominal)} mm"
        )

    if old_tolerance != new_tolerance:
        changes.append(
            f"공차: ±{format_number(old_tolerance)} mm "
            f"→ ±{format_number(new_tolerance)} mm"
        )

    if old_material != new_material:
        changes.append(
            f"재질: {old_material} → {new_material}"
        )

    if old_heat != new_heat:
        changes.append(
            f"열처리: {old_heat} → {new_heat}"
        )

    st.markdown("#### 주요 설계변경")

    st.write(
        f"Revision **{old_revision} → {new_revision}**"
    )

    if changes:
        for change in changes:
            st.write(f"- {change}")
    else:
        st.info(
            "Parser로 추출된 주요 품질특성에서 "
            "변경사항이 확인되지 않았습니다."
        )


# ============================================================
# 전체 첨부문서 요약
# ============================================================

def show_document_analysis(parsed_documents):
    if not parsed_documents:
        st.warning("분석 가능한 첨부문서가 없습니다.")
        return

    success_count = sum(
        1
        for document in parsed_documents
        if document.get("parse_status")
        in {"SUCCESS", "WARNING"}
    )

    st.markdown(
        f"### 첨부문서 분석 "
        f"{success_count}/{len(parsed_documents)} 완료"
    )

    successful_documents = [
        document
        for document in parsed_documents
        if document.get("parse_status")
        in {"SUCCESS", "WARNING"}
    ]

    drawings = [
        document
        for document in successful_documents
        if document.get("document_type") == "DRAWING"
    ]

    drawings = sorted(
        drawings,
        key=lambda document: str(
            (document.get("structured_data") or {}).get(
                "revision",
                "",
            )
        ),
    )

    for index, drawing in enumerate(drawings):
        if len(drawings) >= 2:
            if index == 0:
                role = "변경 전 도면"
            elif index == len(drawings) - 1:
                role = "변경 후 도면"
            else:
                role = "중간 Revision 도면"
        else:
            role = "도면"

        show_drawing_summary(
            drawing,
            role,
        )

        st.divider()

    if len(drawings) >= 2:
        show_design_change_summary(
            drawings
        )

        st.divider()

    for document in successful_documents:
        document_type = document.get(
            "document_type"
        )

        if document_type == "DRAWING":
            continue

        if document_type == "INSPECTION_REPORT":
            show_inspection_summary(
                document
            )

        elif document_type in {
            "MATERIAL_CERTIFICATE",
            "HEAT_TREATMENT_CERTIFICATE",
        }:
            show_certificate_summary(
                document
            )

        else:
            label = DOCUMENT_TYPE_LABELS.get(
                document_type,
                document_type,
            )

            st.markdown(
                f"#### {label}"
            )

            st.write(
                document.get(
                    "file_name",
                    "-",
                )
            )

        st.divider()

    # 오류 문서
    errors = [
        document
        for document in parsed_documents
        if document.get("parse_status")
        not in {"SUCCESS", "WARNING"}
    ]

    if errors:
        st.markdown("#### 분석 실패/미지원 문서")

        for document in errors:
            st.error(
                f"{document.get('file_name', '-')} · "
                f"{document.get('parse_status', 'UNKNOWN')} · "
                f"{document.get('error') or '분석할 수 없는 문서'}"
            )

    # 원본 데이터는 개발 확인용으로만 숨김
    with st.expander("개발자용 원본 데이터"):
        st.caption(
            "Parser가 추출한 구조화 데이터를 확인하기 위한 "
            "개발/디버깅용 영역입니다."
        )

        for document in parsed_documents:
            st.markdown(
                f"**{document.get('file_name', '-')}**"
            )

            st.write(
                "문서 유형:",
                document.get(
                    "document_type",
                    "UNKNOWN",
                ),
            )

            st.write(
                "Parser 상태:",
                document.get(
                    "parse_status",
                    "UNKNOWN",
                ),
            )

            if document.get("structured_data") is not None:
                st.json(
                    document.get(
                        "structured_data",
                        {},
                    )
                )

            if document.get("error"):
                st.error(
                    document.get("error")
                )

            st.divider()


# ============================================================
# Agent 결과 화면
# ============================================================

def show_agent_result(state, case_id):
    st.subheader(
        f"Case Overview · {case_id}"
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "최종 판정",
            state.get("decision", "-"),
        )

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

    missing = state.get(
        "missing_items",
        [],
    )

    with col3:
        st.metric(
            "확인 필요",
            len(missing),
        )

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

    show_case_status(state)

    st.divider()

    show_result(state)

    st.divider()

    show_followup(state)

    st.divider()

    with st.expander("Agent 실행 이력"):
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
        # 메일 역할 / 처리상태
        # ----------------------------------------------------

        if mail_type == "NEW":
            mail_role = "신규 Case"
            process_status = "Case 생성 대기"

        elif mail_type == "INITIAL":
            mail_role = "신규 Case"
            process_status = "Case 생성 및 검증 완료"

        elif mail_type == "SUPPLEMENTAL":
            mail_role = "보완 / 후속 자료"
            process_status = "기존 Case 연결"

        else:
            mail_role = mail_type
            process_status = "-"

        # ----------------------------------------------------
        # 메일 카드
        # ----------------------------------------------------

        with st.expander(
            f"{index}. {subject}"
        ):

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.write("**발신자**")
                st.write(
                    mail.get(
                        "from",
                        "-",
                    )
                )

            with col2:
                st.write("**메일 역할**")
                st.write(mail_role)

            with col3:
                st.write("**처리 상태**")
                st.write(process_status)

            with col4:
                st.write("**연결 Case**")
                st.write(
                    case_id
                    if case_id
                    else "-"
                )

            st.caption(
                mail.get(
                    "reason",
                    "-",
                )
            )

            # ------------------------------------------------
            # 첨부문서 분석
            # ------------------------------------------------

            st.divider()

            show_document_analysis(
                parsed_documents
            )

            # ------------------------------------------------
            # 메일 본문은 보조 정보로 숨김
            # ------------------------------------------------

            with st.expander(
                "메일 원문 보기"
            ):
                st.write(
                    "**Gmail Thread ID**"
                )

                st.code(
                    thread_id
                    if thread_id
                    else "-"
                )

                st.write("**본문**")

                body = mail.get(
                    "body",
                    "",
                )

                st.text(
                    body
                    if body
                    else "(본문 없음)"
                )

            # =================================================
            # 신규 Case 생성 + Agent 검증
            # =================================================

            if mail_type == "NEW":

                st.divider()

                start_button = st.button(
                    "Case 생성 및 검증 시작",
                    key=(
                        f"create_case_"
                        f"{index}_{thread_id}"
                    ),
                    type="primary",
                    use_container_width=True,
                )

                if start_button:

                    try:

                        # ------------------------------------
                        # 1. Gmail → Case 생성
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

                            st.session_state[
                                "last_agent_state"
                            ] = state

                            st.session_state[
                                "last_case_id"
                            ] = created_case_id

                            decision = state.get(
                                "decision",
                                "-",
                            )

                            case_status = state.get(
                                "case_status",
                                "-",
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
            # 이미 처리된 최초 메일
            # =================================================

            elif mail_type == "INITIAL":

                st.divider()

                st.success(
                    f"{case_id}를 생성한 "
                    "최초 설계변경 요청 메일입니다."
                )

                st.caption(
                    "이 메일은 이미 Case에 연결되어 있으므로 "
                    "새 Case를 다시 생성하지 않습니다."
                )

            # =================================================
            # 기존 Case 후속자료
            # =================================================

            elif mail_type == "SUPPLEMENTAL":

                st.divider()

                if case_id:
                    st.info(
                        f"{case_id}에 연결된 "
                        "보완/후속 자료입니다."
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