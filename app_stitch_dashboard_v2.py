import streamlit as st
from html import escape as html_escape

from dotenv import load_dotenv



from agent.runner import run_case


def run_case_with_test_db(case_id: str):
    """
    ?? Case? ????? ??? DB?? ????.

    CASE-001: ?? DB -> PASS
    CASE-002: ?? HOLD ?? DB -> HOLD
    CASE-003: REJECT ?? DB -> REJECT

    ?? ?? ??? ?? database ??? DB_PATH?
    ??? ?? ??? ????.
    """
    import importlib
    import pkgutil
    from pathlib import Path

    import database

    db_map = {
        "CASE-002": Path(
            "database/CASE-002_initial_hold_test.db"
        ).resolve(),
        "CASE-003": Path(
            "database/agent_reject_test.db"
        ).resolve(),
    }

    test_db = db_map.get(case_id)

    # CASE-001 ? ?? Case? ?? ?? DB? ??? ??
    if test_db is None:
        return run_case(case_id)

    if not test_db.is_file():
        raise FileNotFoundError(
            f"??? DB? ?? ? ????: {test_db}"
        )

    original_paths = {}

    try:
        for module_info in pkgutil.iter_modules(
            database.__path__
        ):
            name = module_info.name

            if name.startswith(
                ("test_", "import_", "reset_")
            ):
                continue

            module = importlib.import_module(
                f"database.{name}"
            )

            if hasattr(module, "DB_PATH"):
                original_paths[name] = module.DB_PATH
                module.DB_PATH = test_db

        return run_case(case_id)

    finally:
        for name, original_path in original_paths.items():
            module = importlib.import_module(
                f"database.{name}"
            )
            module.DB_PATH = original_path


from database.live_case_service import create_live_case

from database.supplemental_repository import register_supplemental

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

# 기업용 품질관리 대시보드 스타일 (UI 전용)

# ============================================================

st.markdown("""

<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root { --navy:#152a46; --ink:#20334c; --muted:#64748b; --line:#e1e8f0; }

html, body, [class*="css"], [data-testid="stApp"] { font-family:'Inter','Malgun Gothic',sans-serif; }

[data-testid="stAppViewContainer"] { background:#f5f7fb; }

.block-container { max-width:1350px; padding-top:2.2rem; padding-bottom:4rem; }

[data-testid="stHeader"] { background:transparent; }

h1,h2,h3 { color:var(--navy); letter-spacing:-.025em; }

h2 { font-size:1.35rem!important; }

h3 { font-size:1.1rem!important; }

[data-testid="stVerticalBlockBorderWrapper"] > div { border-color:var(--line)!important; }

[data-testid="stMetric"] { background:white; padding:19px 22px; border:1px solid var(--line); border-radius:12px; min-height:116px; box-shadow:0 2px 10px rgba(21,42,70,.035); }

[data-testid="stMetricLabel"] { color:var(--muted); font-size:.86rem; }

[data-testid="stMetricValue"] { color:var(--navy); font-weight:750; }

[data-testid="stExpander"] { border:1px solid var(--line)!important; border-radius:10px!important; background:white; overflow:hidden; }

[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:8px; overflow:hidden; }

[data-testid="stAlert"] { border-radius:9px; }

.stButton > button[kind="primary"] { background:#1c4169!important; border-color:#1c4169!important; color:white!important; border-radius:8px; font-weight:650; }

.stButton > button { border-radius:8px; min-height:39px; }

hr { border-color:var(--line)!important; margin:1.5rem 0!important; }

.aero-header { background:linear-gradient(115deg,#142b49,#224d73); border-radius:15px; padding:27px 32px; margin-bottom:25px; color:white; box-shadow:0 6px 22px rgba(21,42,70,.12); }

.aero-eyebrow { color:#a9c6e3; font-size:.72rem; font-weight:700; letter-spacing:.18em; margin-bottom:9px; }

.aero-brand { color:white; font-size:1.9rem; font-weight:800; letter-spacing:-.04em; margin:0; }

.aero-sub { color:#d7e6f3; font-size:.91rem; margin-top:6px; }

.aero-system { display:inline-block; margin-top:16px; padding:5px 10px; border:1px solid #547b9b; border-radius:30px; font-size:.71rem; color:#d7ebf5; letter-spacing:.07em; }

.aero-section { font-size:.74rem; font-weight:800; letter-spacing:.13em; color:#6381a1; margin:8px 0 5px; }

.aero-section-title { color:#152a46; font-size:1.37rem; font-weight:750; margin-bottom:7px; }

.aero-section-desc { color:#64748b; font-size:.86rem; margin-bottom:15px; }

.aero-case { display:flex; justify-content:space-between; align-items:center; gap:15px; flex-wrap:wrap; margin:10px 0 18px; padding:17px 22px; background:white; border:1px solid var(--line); border-left:5px solid #275782; border-radius:10px; }

.aero-case-name { color:#152a46; font-size:1.08rem; font-weight:750; }

.aero-case-note { color:#64748b; font-size:.76rem; margin-top:3px; }

.aero-pill { border-radius:30px; padding:6px 14px; font-size:.8rem; font-weight:750; }

.aero-pill.pass { background:#e7f5ed; color:#207248; }

.aero-pill.hold { background:#fff2d7; color:#926015; }

.aero-pill.reject { background:#fce7e7; color:#ac3434; }

.aero-pill.other { background:#e8eef5; color:#38516a; }


/* Stitch detail-screen system: derived from the uploaded Stitch designs. */
.aero-detail-heading {font-size:1.05rem;font-weight:800;color:#0e3255;margin:12px 0 4px;}
.aero-detail-desc {font-size:.82rem;color:#64748b;margin-bottom:16px;}
.aero-detail-banner {background:#eaf2ff;border:1px solid #c9dafa;border-left:4px solid #2869d2;padding:12px 15px;border-radius:7px;margin:12px 0 18px;}
[data-testid="stTabs"] button[role="tab"] {font-weight:700;white-space:normal;}
[data-testid="stTabs"] button[aria-selected="true"] {color:#1556b5;border-bottom-color:#1556b5;}
/* Stitch-inspired navigation and operational dashboard */
[data-testid="stSidebar"] { background:#102238; border-right:1px solid #1c3652; }
[data-testid="stSidebar"] * { color:#e6eef8; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { padding:7px 4px; }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) { background:#1354b7; border-radius:7px; }
.aero-header { background:linear-gradient(112deg,#10243e,#183f67)!important; }
.aero-kicker { font-size:.75rem; color:#64748b; font-weight:700; letter-spacing:.08em; }
.aero-dashboard-title { font-size:1.55rem; font-weight:800; color:#10243e; margin:3px 0 7px; }
.aero-dashboard-sub { color:#667b93; font-size:.87rem; margin-bottom:14px; }
.aero-stage { padding:12px; background:#fff; border:1px solid #dae5f1; border-top:3px solid #2c69bd; border-radius:9px; min-height:94px; }
.aero-stage small { color:#687e95; }
.aero-stage strong { display:block; margin-top:7px; font-size:.87rem; color:#16324d; }


/* Stitch-inspired operational components */
.aero-workflow {display:flex;gap:8px;align-items:stretch;margin:16px 0 23px;flex-wrap:wrap}
.aero-node {flex:1;min-width:125px;background:white;border:1px solid #dbe5f1;border-top:3px solid #2563c4;border-radius:7px;padding:13px 11px}
.aero-node-label {font-size:.67rem;letter-spacing:.1em;color:#68809d;font-weight:750}
.aero-node-title {font-size:.86rem;color:#142d4a;font-weight:800;margin:7px 0}
.aero-node-value {font-size:.76rem;color:#385675;overflow-wrap:anywhere}
.aero-panel {border:1px solid #dce5ef;background:#fff;border-radius:10px;padding:16px 18px;margin:12px 0}
.aero-panel-title {font-size:.86rem;font-weight:800;color:#163b65;margin-bottom:9px}
.aero-agent-event {padding:10px 12px;border-left:3px solid #2770c8;background:#f1f6fd;margin:7px 0;border-radius:4px;font-size:.79rem;color:#1a395a}
.aero-agent-event.warn {border-color:#d98a18;background:#fff7e9}
.aero-case-banner {padding:16px 19px;background:#edf4fd;border:1px solid #d4e4f7;border-radius:9px;margin:10px 0 17px}
.aero-case-banner strong {color:#123a66}

</style>

""", unsafe_allow_html=True)



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



def show_validation_plan(state):
    """Agent가 생성한 검증계획을 표시한다."""
    plan = (state.get("tool_results", {})
            .get("validation_plan", {})
            .get("result", {}))
    st.subheader("검증계획")
    if not plan:
        st.info("생성된 검증계획이 없습니다.")
        return
    change_types = plan.get("change_types", [])
    tasks = plan.get("validation_tasks", [])
    required_documents = plan.get("required_documents", [])
    st.write("**설계변경 유형**")
    st.write(", ".join(change_types) if change_types else "없음")
    st.write("**검증항목**")
    if tasks:
        st.dataframe([
            {"변경 유형": task.get("change_type", "-"),
             "필요 문서": task.get("required_document", "-"),
             "검증 내용": task.get("description", "-")}
            for task in tasks
        ], use_container_width=True, hide_index=True)
    else:
        st.info("생성된 검증항목이 없습니다.")
    st.write("**필수 품질문서**")
    st.write(", ".join(required_documents) if required_documents else "없음")


def _ui_text(value):
    return html_escape(str(value if value is not None else "-"))


def show_trace_workflow(state, affected_lots):
    """Display only identifiers returned by the impact tool."""
    impact = ((state.get("tool_results") or {}).get("impact") or {}).get("result") or {}
    if not affected_lots:
        st.info("추적된 영향 Lot이 없습니다. 원본 영향 추적 결과를 확인하세요.")
        return
    st.caption("Drawing → Part → PO → Lot · Agent가 식별한 영향 대상")
    for idx, lot in enumerate(affected_lots, 1):
        if not isinstance(lot, dict):
            st.write(f"대상 {idx}: {lot}")
            continue
        design_result = (
            (state.get("tool_results") or {})
            .get("design_change") or {}
        )
        
        drawing_evidence = design_result.get("evidence") or []
        
        new_drawing = next(
            (
                item for item in drawing_evidence
                if item.get("role") == "NEW_DRAWING"
            ),
            {}
        )
        
        drawing = (
            lot.get("drawing_no")
            or lot.get("drawing_id")
            or new_drawing.get("file_name")
            or "도면 정보 미제공"
        )
        part = lot.get("part_no") or lot.get("part_id") or "Part 정보 미제공"
        po = lot.get("po_no") or lot.get("po_id") or "PO 정보 미제공"
        lot_no = lot.get("lot_no") or lot.get("lot_id") or "Lot 정보 미제공"
        nodes = [("DRAWING", drawing), ("PART", part), ("PURCHASE ORDER", po), ("AFFECTED LOT", lot_no)]
        html = '<div class="aero-workflow">' + ''.join(
            '<div class="aero-node"><div class="aero-node-label">'+_ui_text(label)+'</div>'
            '<div class="aero-node-title">'+_ui_text(value)+'</div></div>'
            for label,value in nodes) + '</div>'
        st.markdown(html, unsafe_allow_html=True)
        details = {"Lot": lot_no, "생산일": lot.get("production_date"),
                   "적용일": lot.get("effectivity_date"), "적용 Revision": lot.get("required_revision"),
                   "실제 Revision": lot.get("revision")}
        st.dataframe([details], hide_index=True, use_container_width=True)


def show_quality_matrix(state):
    """Render raw quality tool results without manufacturing measurement values."""
    quality = ((state.get("tool_results") or {}).get("quality") or {}).get("result") or {}
    lot_results = quality.get("lot_results") or []
    st.markdown('<div class="aero-panel-title">Lot별 품질검증 결과</div>', unsafe_allow_html=True)
    if lot_results:
        rows = []
        for item in lot_results:
            if not isinstance(item, dict):
                continue
            rows.append({"Lot":item.get("lot_no") or item.get("lot_id") or "-",
                         "판정":item.get("decision") or "-",
                         "검증 사유":item.get("reason") or item.get("message") or "원본 결과에서 확인"})
        if rows:
            st.dataframe(rows, hide_index=True, use_container_width=True)
    else:
        st.info("Lot별 세부 판정 데이터가 없습니다.")
    evidence = state.get("evidence") or []
    st.markdown('<div class="aero-panel-title">근거문서 및 검증 항목</div>', unsafe_allow_html=True)
    if evidence:
        if all(isinstance(item, dict) for item in evidence):

            document_labels = {
                "OLD_DRAWING": "변경 전 도면",
                "NEW_DRAWING": "변경 후 도면",
            }

            rows = []

            for item in evidence:
                role = item.get("role")
                filename = item.get("file_name") or "-"

                if role in document_labels:
                    document_type = document_labels[role]
                elif filename.upper().startswith("INS"):
                    document_type = "검사성적서"
                elif filename.upper().startswith("MAT"):
                    document_type = "소재성적서"
                elif filename.upper().startswith("HT"):
                    document_type = "열처리성적서"
                else:
                    document_type = role or "유형 미확인"

                rows.append({
                    "문서 유형": document_type,
                    "파일명": filename,
                    "Revision": item.get("revision") or "-",
                    "Lot": item.get("lot_id") or "-"
                })

            st.dataframe(
                rows,
                hide_index=True,
                use_container_width=True
            )

        else:
            st.write(evidence)
    else:
        st.info("표시할 근거 데이터가 없습니다.")


def show_agent_pipeline(state):
    trace = state.get("agent_trace") or []
    if not trace:
        st.info("실행 이력이 없습니다.")
        return
    for i, item in enumerate(trace,1):
        if not isinstance(item,dict):
            st.write(f"{i}. {item}")
            continue
        tool = item.get("tool") or item.get("selected_tool") or item.get("tool_name") or "Agent step"
        source = item.get("decision_source") or item.get("source") or "-"
        outcome = item.get("result") or item.get("status") or "-"
        warn = "warn" if str(tool) in ("replan","followup") else ""
        st.markdown(f'<div class="aero-agent-event {warn}"><b>{i:02d} · {_ui_text(tool)}</b> · {_ui_text(source)} · {_ui_text(outcome)}</div>', unsafe_allow_html=True)


def show_agent_result(state, case_id):

    decision_label = str(state.get("decision") or "PROCESSING").upper()

    decision_style = decision_label.lower() if decision_label in {"PASS", "HOLD", "REJECT"} else "other"

    st.markdown(

        f'<div class="aero-section">QUALITY CONTROL / CASE DETAIL</div>'

        f'<div class="aero-case"><div><div class="aero-case-name">{case_id}</div>'

        f'<div class="aero-case-note">설계변경 영향분석 및 품질검증 결과</div></div>'

        f'<span class="aero-pill {decision_style}">{decision_label}</span></div>',

        unsafe_allow_html=True,

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

            "Agent 실행 단계",

            len(state.get("agent_trace", [])),

        )



    st.divider()

    # All tabs use the existing Agent state. No demonstration numbers or
    # independent quality decisions are generated in the UI.
    tab_overview, tab_plan, tab_quality, tab_followup, tab_trace = st.tabs([
        "종합 결과", "01·02 설계변경·검증계획", "03·04 영향추적·품질검증",
        "05 후속조치·재검증", "Agent 실행 이력",
    ])
    with tab_overview:
        st.markdown('<div class="aero-detail-heading">5단계 품질검증 진행 상태</div>', unsafe_allow_html=True)
        show_case_status(state)
        st.markdown('<div class="aero-detail-heading">최종 품질판정</div>', unsafe_allow_html=True)
        show_result(state)
    with tab_plan:
        st.markdown('<div class="aero-detail-heading">설계변경 분석 및 검증계획</div>', unsafe_allow_html=True)
        st.caption("Stitch 설계변경·검증계획 화면을 실제 Agent 결과에 연결한 보기")
        change = (tool_results.get("design_change") or {}).get("result") or {}
        show_validation_plan(state)
        adjustments = state.get("plan_adjustments") or []
        if adjustments:
            st.markdown("**LLM 검증계획 조정 이력**")
            for idx, adjustment in enumerate(adjustments, 1):
                with st.expander(f"계획 조정 {idx} · {adjustment.get('decision_source', '-')}"):
                    st.write("선택 사유:", adjustment.get("reason") or "기록 없음")
                    st.write("추가 검증항목:", adjustment.get("additional_checks") or "없음")
                    st.write("적용 문서:", ", ".join(adjustment.get("effective_required_documents") or []))
    with tab_quality:
        st.markdown('<div class="aero-detail-heading">Effectivity 기반 영향범위 추적</div>', unsafe_allow_html=True)
        st.caption("변경 적용 대상 Lot과 실제 품질문서 검증 결과")
        impact_result = (impact.get("result") or {})
        st.metric("영향 대상 Lot", len(affected_lots))
        show_trace_workflow(state, affected_lots)
        st.markdown('<div class="aero-detail-heading">증거 기반 품질검증</div>', unsafe_allow_html=True)
        show_quality_matrix(state)
        with st.expander("기존 품질검증 결과 보기"):
            show_result(state)
    with tab_followup:
        st.markdown('<div class="aero-detail-heading">후속조치 및 재검증</div>', unsafe_allow_html=True)
        show_followup(state)
        st.caption("보완자료 수신과 재검증 실행은 기존 Case 수신함 기능을 이용합니다.")
    with tab_trace:
        st.markdown('<div class="aero-detail-heading">AI Agent Tool 실행·동적 재계획 로그</div>', unsafe_allow_html=True)
        st.metric("Agent 실행 단계", len(state.get("agent_trace") or []))
        st.metric("검증계획 개정 횟수", state.get("plan_revision") or 0)
        show_history(state)



# Sidebar: UI navigation only. Agent/DB execution remains unchanged.
with st.sidebar:
    st.markdown("### ◈ AeroChange Trace")
    st.caption("항공기 설계변경 품질검증 · 5단계 Agent")
    st.divider()
    page = st.radio(
        "업무 메뉴",
        ["종합 관제 대시보드", "Case 수신함", "Case 직접 검증", "최근 Agent 결과"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("설계변경 분석 → 검증계획 → 영향범위 추적 → 품질검증 → 후속조치")


def show_operations_overview():
    """Stitch-style dashboard using actual results from this Streamlit session."""
    st.markdown('<div class="aero-kicker">OPERATIONS / QUALITY CONTROL</div>', unsafe_allow_html=True)
    st.markdown('<div class="aero-dashboard-title">AeroChange Trace AI 종합 관제 대시보드</div>', unsafe_allow_html=True)
    st.markdown('<div class="aero-dashboard-sub">설계변경 영향추적 · 협력업체 품질검증 · AI Agent 동적 재계획</div>', unsafe_allow_html=True)
    state = st.session_state.get("last_agent_state")
    case_id = st.session_state.get("last_case_id")
    if state is None:
        st.info("아직 이 세션에서 실행한 Case가 없습니다. Case 수신함 또는 Case 직접 검증에서 실행하세요.")
        st.caption("Stitch 디자인의 PASS/HOLD/REJECT 예시 집계는 실제 데이터가 아니므로 표시하지 않습니다.")
        return
    decision = str(state.get("decision") or "PROCESSING").upper()
    results = state.get("tool_results") or {}
    lots = ((results.get("impact") or {}).get("result") or {}).get("affected_lots") or []
    a,b,c,d = st.columns(4)
    with a:
        st.markdown(
            f"""
            <div style="background: white; border: 1px solid #dbe3ee;
            border-radius: 9px; padding: 16px;
min-height: 106px; box-sizing: border-box;">
                <div style="font-size: 14px; color: #64748b;">
                    최근 실행 Case
                </div>
                <div style="font-size: 23px; font-weight: 700;
                            white-space: nowrap; color: #10233e;">
                    {_ui_text(case_id or "-")}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    b.metric("최종 판정", decision)
    c.metric("영향 Lot", len(lots))
    d.metric("Agent 실행 단계", len(state.get("agent_trace") or []))
    st.markdown("#### 5단계 검증 파이프라인")
    stages = [("01", "설계변경 분석", "design_change"), ("02", "검증계획 생성", "validation_plan"),
              ("03", "영향범위 추적", "impact"), ("04", "품질검증", "quality"), ("05", "후속조치", "followup")]
    cols = st.columns(5)
    for col, (number, title, key) in zip(cols, stages):
        status = "완료" if results.get(key) else ("불필요 · PASS" if key == "followup" and decision == "PASS" else "대기")
        with col:
            st.markdown(f'<div class="aero-stage"><small>STAGE {number}</small><strong>{title}</strong><small>{status}</small></div>', unsafe_allow_html=True)
    left,right = st.columns([1.6,1],gap="large")
    with left:
        st.markdown("#### 최근 실행 Case")
        st.markdown(f'<div class="aero-case-banner"><strong>{_ui_text(case_id or "-")}</strong><br>최종 판정: <b>{_ui_text(decision)}</b> · 영향 Lot: {len(lots)}건</div>', unsafe_allow_html=True)
        st.markdown("**영향범위 추적**")
        show_trace_workflow(state,lots)
        st.markdown("**품질검증 요약**")
        show_quality_matrix(state)
    with right:
        st.markdown("#### AI Agent 자율 실행")
        st.caption("실제 Tool 실행 및 동적 재계획 이력")
        st.metric("검증계획 개정",state.get("plan_revision") or 0)
        show_agent_pipeline(state)
    st.divider()
    with st.expander("Case 상세 결과 및 전체 검증 탭"):
        show_agent_result(state, case_id or "-")


# ============================================================

# Header

# ============================================================



if page == "종합 관제 대시보드":
    show_operations_overview()
elif page == "최근 Agent 결과":
    previous = st.session_state.get("last_agent_state")
    if previous:
        show_agent_result(previous, st.session_state.get("last_case_id") or "-")
    else:
        st.info("현재 세션에 Agent 실행 결과가 없습니다.")
elif page == "Case 수신함":
    st.markdown("""

    <div class="aero-header">

      <div class="aero-eyebrow">AEROSPACE · QUALITY INTELLIGENCE</div>

      <div class="aero-brand">AeroChange Trace AI</div>

      <div class="aero-sub">항공기 설계변경 영향추적 · 협력업체 품질검증 AI Agent</div>

      <div class="aero-system">● QUALITY OPERATIONS WORKSPACE</div>

    </div>

    """, unsafe_allow_html=True)





    # ============================================================

    # Gmail 수신 메일

    # ============================================================



    st.markdown("""

    <div class="aero-section">01 / WORK QUEUE</div>

    <div class="aero-section-title">수신 메일 · Case Inbox</div>

    <div class="aero-section-desc">설계변경 요청과 보완자료를 확인하고 연결된 Case의 검증을 진행합니다.</div>

    """, unsafe_allow_html=True)



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



                        supplemental_documents = [

                            document

                            for document in parsed_documents

                            if document.get("parse_status") in {"SUCCESS", "WARNING"}

                            and document.get("document_type") in {

                                "INSPECTION_REPORT",

                                "MATERIAL_CERTIFICATE",

                                "HEAT_TREATMENT_CERTIFICATE",

                            }

                            and isinstance(document.get("structured_data"), dict)

                        ]



                        if supplemental_documents:

                            supplemental_button = st.button(

                                "보완자료 등록 및 재검증",

                                key=f"supplemental_{index}_{mail.get('message_id') or thread_id}",

                                type="primary",

                                use_container_width=True,

                            )



                            if supplemental_button:

                                try:

                                    message_id = mail.get("message_id") or mail.get("id")



                                    if not message_id:

                                        raise ValueError(

                                            "Gmail message_id를 확인할 수 없습니다."

                                        )



                                    attachments = [

                                        {

                                            "file_name": document.get("file_name"),

                                            "file_path": document.get("file_path"),

                                            "document_type": document.get("document_type"),

                                            "parsed_data": document.get("structured_data"),

                                        }

                                        for document in supplemental_documents

                                    ]



                                    with st.spinner(

                                        f"{case_id}에 보완자료를 등록하고 있습니다..."

                                    ):

                                        register_kwargs = {}

                                        if case_id == "CASE-002":
                                            register_kwargs["db_path"] = Path(
                                                "database/CASE-002_initial_hold_test.db"
                                            ).resolve()

                                        register_result = register_supplemental(

                                            case_id=case_id,

                                            message_id=message_id,

                                            attachments=attachments,

                                            **register_kwargs,

                                        )



                                    added_count = register_result.get("added_count", 0)

                                    skipped_count = register_result.get("skipped_count", 0)



                                    if added_count:

                                        st.success(

                                            f"보완자료 {added_count}건을 "

                                            f"{case_id}에 등록했습니다."

                                        )



                                    if skipped_count:

                                        st.info(

                                            f"이미 등록된 보완자료 {skipped_count}건은 "

                                            "중복 저장하지 않았습니다."

                                        )



                                    with st.spinner(

                                        f"{case_id}를 재검증하고 있습니다..."

                                    ):

                                        state = (
                                            run_case_with_test_db(case_id)
                                            if case_id == "CASE-002"
                                            else run_case(case_id)
                                        )



                                    st.session_state["last_agent_state"] = state

                                    st.session_state["last_case_id"] = case_id



                                    decision = state.get("decision", "-")

                                    case_status = state.get("case_status", "-")



                                    if decision == "PASS":

                                        st.success(

                                            f"{case_id} 재검증 결과: PASS"

                                        )

                                    elif decision == "HOLD":

                                        st.warning(

                                            f"{case_id} 재검증 결과: HOLD"

                                        )

                                    elif decision == "REJECT":

                                        st.error(

                                            f"{case_id} 재검증 결과: REJECT"

                                        )

                                    else:

                                        st.info(

                                            f"{case_id} 재검증 결과: {decision}"

                                        )



                                    st.write(f"**Case 상태:** {case_status}")

                                    st.divider()

                                    show_agent_result(state, case_id)



                                except Exception as error:

                                    st.error(

                                        "보완자료 등록 또는 재검증 중 "

                                        f"오류가 발생했습니다: {error}"

                                    )

                        else:

                            st.warning(

                                "등록 가능한 보완 품질문서가 없습니다."

                            )





if page == "Case 직접 검증":
    st.divider()





    # ============================================================

    # 개발 / 테스트용 Case 직접 실행

    # ============================================================



    st.markdown("""

    <div class="aero-section">02 / DEVELOPMENT TOOLS</div>

    <div class="aero-section-title">Case 직접 검증</div>

    """, unsafe_allow_html=True)



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



                state = run_case_with_test_db(

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
