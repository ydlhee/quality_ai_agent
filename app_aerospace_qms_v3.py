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
from mail.gmail_sender import get_gmail_account_email
from email.utils import parseaddr

from ui.components import (

    show_case_status,

    show_result,

    show_followup,

    show_history,

)





load_dotenv()


# ============================================================
# V3 공통 작업 상태
# ============================================================
# Streamlit 페이지/메뉴 이동 및 rerun 이후에도
# 현재 작업 중인 Case와 UI 상태를 유지한다.

_STATE_DEFAULTS = {
    "last_agent_state": None,
    "last_case_id": None,
    "manual_case_edit_mode": False,
    "inbox_result_open": False,
}

for _key, _default in _STATE_DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _default






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


/* =========================================================
   V3 DENSE AEROSPACE QMS DASHBOARD
   ========================================================= */

.qms-topbar {
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:16px;
    background:#ffffff;
    border:1px solid #dbe5ef;
    border-top:3px solid #1769d2;
    border-radius:7px;
    padding:14px 17px;
    margin-bottom:15px;
}

.qms-brand-small {
    font-size:10px;
    font-weight:800;
    letter-spacing:.12em;
    color:#1769d2;
}

.qms-brand-title {
    margin-top:3px;
    font-size:18px;
    line-height:1.2;
    font-weight:800;
    color:#10243e;
}

.qms-brand-sub {
    margin-top:4px;
    font-size:11px;
    color:#718096;
}

.qms-program {
    text-align:right;
}

.qms-program-label {
    font-size:9px;
    font-weight:800;
    letter-spacing:.1em;
    color:#7a8da0;
}

.qms-program-name {
    margin-top:3px;
    font-size:14px;
    font-weight:800;
    color:#163a5f;
}

.qms-status-row {
    display:flex;
    gap:5px;
    justify-content:flex-end;
    flex-wrap:wrap;
    margin-top:6px;
}

.qms-badge {
    display:inline-block;
    padding:3px 7px;
    border-radius:4px;
    font-size:9px;
    font-weight:800;
    letter-spacing:.03em;
    border:1px solid #d9e3ec;
    background:#f3f6f9;
    color:#536a7e;
}

.qms-badge.blue {
    color:#1557b0;
    background:#edf4ff;
    border-color:#cbdcf4;
}

.qms-badge.green {
    color:#167252;
    background:#edf8f3;
    border-color:#c9e8da;
}

.qms-badge.amber {
    color:#95600b;
    background:#fff6e3;
    border-color:#efd9aa;
}

.qms-badge.red {
    color:#b33a40;
    background:#fdecee;
    border-color:#f0c9cc;
}

.qms-section-label {
    margin-top:16px;
    margin-bottom:3px;
    font-size:9px;
    font-weight:800;
    letter-spacing:.11em;
    color:#6685a4;
}

.qms-section-title {
    margin-bottom:10px;
    font-size:15px;
    font-weight:800;
    color:#10243e;
}

.qms-grid {
    display:grid;
    grid-template-columns:repeat(5, 1fr);
    gap:8px;
    margin-bottom:14px;
}

.qms-kpi {
    background:#ffffff;
    border:1px solid #dbe5ef;
    border-radius:6px;
    padding:11px 12px;
    min-height:76px;
}

.qms-kpi-label {
    font-size:9px;
    font-weight:700;
    color:#718096;
    letter-spacing:.04em;
}

.qms-kpi-value {
    margin-top:6px;
    font-size:22px;
    font-weight:800;
    color:#10243e;
}

.qms-kpi-note {
    margin-top:2px;
    font-size:9px;
    color:#8a9aaa;
}

.qms-two {
    display:grid;
    grid-template-columns:1.55fr 1fr;
    gap:10px;
    margin-bottom:10px;
}

.qms-two-even {
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:10px;
    margin-bottom:10px;
}

.qms-panel {
    background:#ffffff;
    border:1px solid #dbe5ef;
    border-radius:6px;
    overflow:hidden;
}

.qms-panel-head {
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:8px;
    padding:9px 11px;
    background:#f8fafc;
    border-bottom:1px solid #e3eaf1;
}

.qms-panel-title {
    font-size:10px;
    font-weight:800;
    letter-spacing:.055em;
    color:#234764;
}

.qms-panel-body {
    padding:10px 11px;
}

.qms-case-row {
    display:grid;
    grid-template-columns:90px 1fr 115px 75px;
    align-items:center;
    gap:8px;
    padding:8px 4px;
    border-bottom:1px solid #edf1f5;
}

.qms-case-row:last-child {
    border-bottom:none;
}

.qms-case-id {
    font-size:11px;
    font-weight:800;
    color:#153c62;
}

.qms-case-desc {
    font-size:10px;
    color:#566f85;
}

.qms-case-flow {
    font-size:9px;
    color:#7b8fa1;
}

.qms-status {
    text-align:center;
    padding:3px 6px;
    border-radius:4px;
    font-size:9px;
    font-weight:800;
}

.qms-status.pass {
    background:#eaf7f1;
    color:#167252;
}

.qms-status.hold {
    background:#fff5df;
    color:#9a650d;
}

.qms-status.reject {
    background:#fdecee;
    color:#b33a40;
}

.qms-status.ready {
    background:#edf4ff;
    color:#1557b0;
}

.qms-mini-table {
    width:100%;
    border-collapse:collapse;
}

.qms-mini-table th {
    text-align:left;
    padding:6px 5px;
    font-size:8px;
    color:#7a8da0;
    letter-spacing:.05em;
    border-bottom:1px solid #dde5ed;
}

.qms-mini-table td {
    padding:7px 5px;
    font-size:9px;
    color:#334a60;
    border-bottom:1px solid #edf1f5;
}

.qms-mini-table tr:last-child td {
    border-bottom:none;
}

.qms-thread {
    display:grid;
    grid-template-columns:repeat(7, 1fr);
    gap:5px;
}

.qms-thread-node {
    position:relative;
    padding:9px 7px;
    background:#f8fafc;
    border:1px solid #dce5ee;
    border-top:2px solid #1769d2;
    border-radius:5px;
}

.qms-thread-node::after {
    content:"›";
    position:absolute;
    right:-6px;
    top:22px;
    z-index:2;
    font-weight:800;
    color:#7d91a5;
}

.qms-thread-node:last-child::after {
    display:none;
}

.qms-thread-label {
    font-size:7px;
    font-weight:800;
    letter-spacing:.07em;
    color:#7890a5;
}

.qms-thread-value {
    margin-top:4px;
    font-size:9px;
    font-weight:750;
    color:#173b5d;
}

.qms-agent-row {
    display:grid;
    grid-template-columns:26px 1fr 65px;
    align-items:center;
    gap:7px;
    padding:6px 4px;
    border-bottom:1px solid #edf1f5;
}

.qms-agent-row:last-child {
    border-bottom:none;
}

.qms-agent-num {
    font-size:8px;
    font-weight:800;
    color:#7d92a5;
}

.qms-agent-tool {
    font-size:9px;
    font-weight:700;
    color:#304f69;
}

.qms-agent-state {
    text-align:right;
    font-size:8px;
    font-weight:800;
    color:#1769d2;
}

.qms-risk {
    display:grid;
    grid-template-columns:1fr 1fr 1fr;
    gap:6px;
}

.qms-risk-card {
    padding:9px;
    border:1px solid #e1e8ef;
    border-radius:5px;
    background:#fafbfd;
}

.qms-risk-name {
    font-size:8px;
    color:#75899b;
}

.qms-risk-value {
    margin-top:4px;
    font-size:12px;
    font-weight:800;
    color:#183b5b;
}

.qms-note {
    padding:8px 10px;
    background:#f2f7fd;
    border-left:3px solid #1769d2;
    font-size:9px;
    color:#4c667d;
    line-height:1.55;
}

@media (max-width: 1050px) {
    .qms-grid {
        grid-template-columns:repeat(2,1fr);
    }

    .qms-two,
    .qms-two-even {
        grid-template-columns:1fr;
    }

    .qms-thread {
        grid-template-columns:repeat(2,1fr);
    }
}

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
    """Dense Stitch-style aerospace quality operations dashboard."""

    state = st.session_state.get("last_agent_state")
    case_id = st.session_state.get("last_case_id")

    if state:
        decision = str(state.get("decision") or "PROCESSING").upper()
        results = state.get("tool_results") or {}
        lots = (
            ((results.get("impact") or {}).get("result") or {})
            .get("affected_lots") or []
        )
        trace_count = len(state.get("agent_trace") or [])
        plan_revision = state.get("plan_revision") or 0
    else:
        decision = "READY"
        results = {}
        lots = []
        trace_count = 0
        plan_revision = 0

    # --------------------------------------------------------
    # Top program context
    # --------------------------------------------------------
    st.markdown(
        '<div class="qms-topbar">'
        '<div>'
        '<div class="qms-brand-small">AEROSPACE QUALITY MANAGEMENT</div>'
        '<div class="qms-brand-title">AeroChange Trace AI</div>'
        '<div class="qms-brand-sub">'
        'Engineering Change · Configuration Control · Supplier Quality'
        '</div>'
        '</div>'
        '<div class="qms-program">'
        '<div class="qms-program-label">ACTIVE PROGRAM · DEMO ENVIRONMENT</div>'
        '<div class="qms-program-name">KF-21 BORAMAE</div>'
        '<div class="qms-status-row">'
        '<span class="qms-badge blue">QUALITY OPERATIONS</span>'
        '<span class="qms-badge green">● SYSTEM ONLINE</span>'
        '<span class="qms-badge blue">AI AGENT READY</span>'
        '</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="qms-section-label">PROGRAM CONTROL / QUALITY OVERVIEW</div>'
        '<div class="qms-section-title">설계변경 품질 운영 현황</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # KPI overview
    # --------------------------------------------------------
    active_case_value = _ui_text(case_id) if state else "03"
    quality_gate_value = _ui_text(decision) if state else "READY"
    affected_value = str(len(lots)) if state else "03"
    agent_value = str(trace_count) if state else "05"
    revision_value = str(plan_revision) if state else "—"

    st.markdown(
        '<div class="qms-grid">'
        '<div class="qms-kpi">'
        '<div class="qms-kpi-label">DEMO TEST CASES</div>'
        '<div class="qms-kpi-value">03</div>'
        '<div class="qms-kpi-note">PASS · HOLD · REJECT</div>'
        '</div>'
        '<div class="qms-kpi">'
        '<div class="qms-kpi-label">CURRENT QUALITY GATE</div>'
        f'<div class="qms-kpi-value">{quality_gate_value}</div>'
        '<div class="qms-kpi-note">Latest Agent decision</div>'
        '</div>'
        '<div class="qms-kpi">'
        '<div class="qms-kpi-label">AFFECTED LOT</div>'
        f'<div class="qms-kpi-value">{affected_value}</div>'
        '<div class="qms-kpi-note">Effectivity trace</div>'
        '</div>'
        '<div class="qms-kpi">'
        '<div class="qms-kpi-label">AGENT PROCESS</div>'
        f'<div class="qms-kpi-value">{agent_value}</div>'
        '<div class="qms-kpi-note">Autonomous workflow</div>'
        '</div>'
        '<div class="qms-kpi">'
        '<div class="qms-kpi-label">PLAN REVISION</div>'
        f'<div class="qms-kpi-value">{revision_value}</div>'
        '<div class="qms-kpi-note">Dynamic replanning</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # Case operations + risk monitor
    # --------------------------------------------------------
    st.markdown(
        '<div class="qms-two">'
        '<div class="qms-panel">'
        '<div class="qms-panel-head">'
        '<div class="qms-panel-title">ENGINEERING CHANGE CASE CONTROL</div>'
        '<span class="qms-badge blue">3 DEMO CASES</span>'
        '</div>'
        '<div class="qms-panel-body">'
        '<div class="qms-case-row">'
        '<div class="qms-case-id">CASE-001</div>'
        '<div><div class="qms-case-desc">정상 품질검증 시나리오</div>'
        '<div class="qms-case-flow">Design Change → Verification → Close</div></div>'
        '<div class="qms-case-flow">Rev.B → Rev.C</div>'
        '<div class="qms-status pass">PASS</div>'
        '</div>'
        '<div class="qms-case-row">'
        '<div class="qms-case-id">CASE-002</div>'
        '<div><div class="qms-case-desc">측정값 누락 · 보완요청 시나리오</div>'
        '<div class="qms-case-flow">Verification → Hold → Correction</div></div>'
        '<div class="qms-case-flow">Rev.B → Rev.C</div>'
        '<div class="qms-status hold">HOLD</div>'
        '</div>'
        '<div class="qms-case-row">'
        '<div class="qms-case-id">CASE-003</div>'
        '<div><div class="qms-case-desc">품질 부적합 · 시정조치 시나리오</div>'
        '<div class="qms-case-flow">Verification → Reject → Action</div></div>'
        '<div class="qms-case-flow">Rev.B → Rev.C</div>'
        '<div class="qms-status reject">REJECT</div>'
        '</div>'
        '</div>'
        '</div>'

        '<div class="qms-panel">'
        '<div class="qms-panel-head">'
        '<div class="qms-panel-title">QUALITY RISK MONITOR</div>'
        '<span class="qms-badge green">MONITORING</span>'
        '</div>'
        '<div class="qms-panel-body">'
        '<div class="qms-risk">'
        '<div class="qms-risk-card">'
        '<div class="qms-risk-name">PASS</div>'
        '<div class="qms-risk-value">01</div>'
        '</div>'
        '<div class="qms-risk-card">'
        '<div class="qms-risk-name">HOLD</div>'
        '<div class="qms-risk-value">01</div>'
        '</div>'
        '<div class="qms-risk-card">'
        '<div class="qms-risk-name">REJECT</div>'
        '<div class="qms-risk-value">01</div>'
        '</div>'
        '</div>'
        '<div class="qms-note" style="margin-top:8px;">'
        '대회 시연용 테스트 Case 현황입니다. '
        '실제 Agent 실행 시 하단 검증영역에는 실행 결과가 연결됩니다.'
        '</div>'
        '</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # Engineering change + quality documents
    # --------------------------------------------------------
    st.markdown(
        '<div class="qms-two-even">'
        '<div class="qms-panel">'
        '<div class="qms-panel-head">'
        '<div class="qms-panel-title">ENGINEERING CHANGE CONTROL</div>'
        '<span class="qms-badge blue">REVISION CONTROL</span>'
        '</div>'
        '<div class="qms-panel-body">'
        '<table class="qms-mini-table">'
        '<thead><tr>'
        '<th>CONTROL ITEM</th><th>CHANGE</th><th>VERIFICATION</th>'
        '</tr></thead>'
        '<tbody>'
        '<tr><td>Drawing Revision</td><td>Rev.B → Rev.C</td>'
        '<td><span class="qms-badge green">TRACKED</span></td></tr>'
        '<tr><td>Dimension / Tolerance</td><td>Change Detection</td>'
        '<td><span class="qms-badge blue">AI CHECK</span></td></tr>'
        '<tr><td>Material</td><td>Requirement Comparison</td>'
        '<td><span class="qms-badge blue">AI CHECK</span></td></tr>'
        '<tr><td>Heat Treatment</td><td>Certificate Requirement</td>'
        '<td><span class="qms-badge blue">AI CHECK</span></td></tr>'
        '<tr><td>Effectivity</td><td>Production Lot Scope</td>'
        '<td><span class="qms-badge green">TRACE</span></td></tr>'
        '</tbody>'
        '</table>'
        '</div>'
        '</div>'

        '<div class="qms-panel">'
        '<div class="qms-panel-head">'
        '<div class="qms-panel-title">SUPPLIER QUALITY DOCUMENTS</div>'
        '<span class="qms-badge blue">EVIDENCE CONTROL</span>'
        '</div>'
        '<div class="qms-panel-body">'
        '<table class="qms-mini-table">'
        '<thead><tr>'
        '<th>DOCUMENT</th><th>VERIFICATION</th><th>ROLE</th>'
        '</tr></thead>'
        '<tbody>'
        '<tr><td>Drawing</td><td>Revision / Requirement</td>'
        '<td><span class="qms-badge green">REQUIRED</span></td></tr>'
        '<tr><td>Inspection Report</td><td>Dimension / Lot / Rev</td>'
        '<td><span class="qms-badge green">REQUIRED</span></td></tr>'
        '<tr><td>Material Certificate</td><td>Material Requirement</td>'
        '<td><span class="qms-badge green">REQUIRED</span></td></tr>'
        '<tr><td>Heat Treatment Cert.</td><td>Process Requirement</td>'
        '<td><span class="qms-badge blue">CONDITIONAL</span></td></tr>'
        '<tr><td>Supplemental Evidence</td><td>Hold Revalidation</td>'
        '<td><span class="qms-badge amber">ON DEMAND</span></td></tr>'
        '</tbody>'
        '</table>'
        '</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # Digital thread
    # --------------------------------------------------------
    st.markdown(
        '<div class="qms-panel">'
        '<div class="qms-panel-head">'
        '<div class="qms-panel-title">DIGITAL THREAD / CONFIGURATION TRACEABILITY</div>'
        '<span class="qms-badge green">TRACE READY</span>'
        '</div>'
        '<div class="qms-panel-body">'
        '<div class="qms-thread">'
        '<div class="qms-thread-node"><div class="qms-thread-label">DRAWING</div>'
        '<div class="qms-thread-value">Revision</div></div>'
        '<div class="qms-thread-node"><div class="qms-thread-label">PART</div>'
        '<div class="qms-thread-value">Part No.</div></div>'
        '<div class="qms-thread-node"><div class="qms-thread-label">PURCHASE ORDER</div>'
        '<div class="qms-thread-value">PO</div></div>'
        '<div class="qms-thread-node"><div class="qms-thread-label">LOT</div>'
        '<div class="qms-thread-value">Effectivity</div></div>'
        '<div class="qms-thread-node"><div class="qms-thread-label">INSPECTION</div>'
        '<div class="qms-thread-value">Measurement</div></div>'
        '<div class="qms-thread-node"><div class="qms-thread-label">MATERIAL</div>'
        '<div class="qms-thread-value">Certificate</div></div>'
        '<div class="qms-thread-node"><div class="qms-thread-label">HEAT TREAT</div>'
        '<div class="qms-thread-value">Process Cert.</div></div>'
        '</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # Agent operations + verification pipeline
    # --------------------------------------------------------
    st.markdown(
        '<div class="qms-two-even" style="margin-top:10px;">'
        '<div class="qms-panel">'
        '<div class="qms-panel-head">'
        '<div class="qms-panel-title">AI AGENT OPERATIONS</div>'
        '<span class="qms-badge green">AUTONOMOUS READY</span>'
        '</div>'
        '<div class="qms-panel-body">'
        '<div class="qms-agent-row"><div class="qms-agent-num">01</div>'
        '<div class="qms-agent-tool">Design Change Analysis</div>'
        '<div class="qms-agent-state">READY</div></div>'
        '<div class="qms-agent-row"><div class="qms-agent-num">02</div>'
        '<div class="qms-agent-tool">Validation Planning</div>'
        '<div class="qms-agent-state">READY</div></div>'
        '<div class="qms-agent-row"><div class="qms-agent-num">03</div>'
        '<div class="qms-agent-tool">Effectivity / Impact Trace</div>'
        '<div class="qms-agent-state">READY</div></div>'
        '<div class="qms-agent-row"><div class="qms-agent-num">04</div>'
        '<div class="qms-agent-tool">Quality Verification</div>'
        '<div class="qms-agent-state">READY</div></div>'
        '<div class="qms-agent-row"><div class="qms-agent-num">05</div>'
        '<div class="qms-agent-tool">Follow-up / Revalidation</div>'
        '<div class="qms-agent-state">READY</div></div>'
        '</div>'
        '</div>'

        '<div class="qms-panel">'
        '<div class="qms-panel-head">'
        '<div class="qms-panel-title">QUALITY GATE LOGIC</div>'
        '<span class="qms-badge blue">CONTROL RULE</span>'
        '</div>'
        '<div class="qms-panel-body">'
        '<table class="qms-mini-table">'
        '<thead><tr><th>GATE</th><th>CONDITION</th><th>ACTION</th></tr></thead>'
        '<tbody>'
        '<tr><td><span class="qms-status pass">PASS</span></td>'
        '<td>All verification satisfied</td><td>Case Close</td></tr>'
        '<tr><td><span class="qms-status hold">HOLD</span></td>'
        '<td>Missing / conflicting evidence</td><td>Correction Request</td></tr>'
        '<tr><td><span class="qms-status reject">REJECT</span></td>'
        '<td>Requirement nonconformance</td><td>Corrective Action</td></tr>'
        '</tbody>'
        '</table>'
        '</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # Actual latest Agent result
    # --------------------------------------------------------
    if state:
        st.markdown(
            '<div class="qms-section-label">LIVE AGENT RESULT</div>'
            '<div class="qms-section-title">최근 실행 Case 검증 결과</div>',
            unsafe_allow_html=True,
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Case", case_id or "-")
        c2.metric("최종 판정", decision)
        c3.metric("영향 Lot", len(lots))
        c4.metric("Agent Steps", trace_count)

        left, right = st.columns([1.6, 1], gap="large")

        with left:
            show_trace_workflow(state, lots)
            show_quality_matrix(state)

        with right:
            show_agent_pipeline(state)

        with st.expander("전체 Engineering Change 검증 결과"):
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


                # ================================================
                # 메일 방향 분리
                # ================================================
                # Gmail API는 검색 조건에 맞는 수신/발신 메일을
                # 모두 반환할 수 있다.
                #
                # 따라서 현재 Gmail 인증 계정을 기준으로:
                #
                #   외부 → AeroChange = INBOUND
                #   AeroChange → 외부 = OUTBOUND
                #
                # 으로 명확하게 분리한다.
                #
                # Case Inbox에는 INBOUND 메일만 표시한다.
                # OUTBOUND 메일은 Case 생성/보완자료 등록 대상으로
                # 절대 처리하지 않는다.

                gmail_account = ""

                try:
                    gmail_account = (
                        get_gmail_account_email()
                        or ""
                    ).strip().lower()

                except Exception:
                    gmail_account = ""


                inbound_results = []
                outbound_results = []


                for mail in mail_results:

                    from_value = (
                        mail.get("from")
                        or ""
                    )

                    to_value = (
                        mail.get("to")
                        or ""
                    )


                    from_email = (
                        parseaddr(from_value)[1]
                        or ""
                    ).strip().lower()

                    to_email = (
                        parseaddr(to_value)[1]
                        or ""
                    ).strip().lower()


                    # --------------------------------------------
                    # AeroChange 인증 Gmail 계정이 발신자이면
                    # 우리가 보낸 OUTBOUND 메일
                    # --------------------------------------------

                    if (
                        gmail_account
                        and from_email == gmail_account
                    ):
                        mail["mail_direction"] = "OUTBOUND"

                        outbound_results.append(
                            mail
                        )

                        continue


                    # --------------------------------------------
                    # 그 외 메일은 INBOUND
                    # --------------------------------------------

                    mail["mail_direction"] = "INBOUND"

                    inbound_results.append(
                        mail
                    )


                # Case Inbox에는 외부에서 들어온 메일만 저장
                st.session_state[
                    "mail_results"
                ] = inbound_results


                # 우리가 발송한 메일은 별도 상태로 보관
                # 추후 Outbound / Sent 화면에서도 사용할 수 있다.
                st.session_state[
                    "outbound_mail_results"
                ] = outbound_results


                # 현재 Gmail 계정도 UI 상태로 보관
                st.session_state[
                    "gmail_account_email"
                ] = gmail_account



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



                                # Agent 결과는 아래 session_state 영역에서
                                # rerun 이후에도 계속 표시한다.



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



                # 기존 Case 검증 결과 다시 열기
                if case_id:
                    open_case_button = st.button(
                        f"{case_id} 검증 결과 열기",
                        key=f"open_existing_case_{index}_{case_id}",
                        use_container_width=True,
                    )

                    if open_case_button:
                        try:
                            with st.spinner(
                                f"{case_id} 검증 결과를 불러오고 있습니다..."
                            ):
                                state = run_case(case_id)

                            st.session_state[
                                "last_agent_state"
                            ] = state
                            st.session_state[
                                "last_case_id"
                            ] = case_id

                            # Case 수신함에서 현재 Case 결과가
                            # 열려 있다는 상태를 기억한다.
                            st.session_state[
                                "inbox_result_open"
                            ] = True

                            st.success(
                                f"{case_id} 검증 결과를 불러왔습니다."
                            )

                            st.rerun()

                        except Exception as error:
                            st.error(
                                f"{case_id} 검증 결과를 불러오는 중 "
                                f"오류가 발생했습니다: {error}"
                            )


                # =================================================

                # 기존 Case 후속자료

                # =================================================



                if mail_type == "SUPPLEMENTAL":



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





# ============================================================
# Case 수신함 작업 상태 복원
# ============================================================
# Case 수신함에서 검증 결과를 한 번 열었다면,
# 다른 메뉴로 이동했다가 돌아와도 Agent를 다시 실행하지 않고
# session_state에 저장된 기존 결과를 그대로 표시한다.

if page == "Case 수신함":
    saved_inbox_state = st.session_state.get(
        "last_agent_state"
    )
    saved_inbox_case_id = st.session_state.get(
        "last_case_id"
    )
    inbox_result_open = st.session_state.get(
        "inbox_result_open",
        False,
    )

    if (
        inbox_result_open
        and saved_inbox_state
        and saved_inbox_case_id
    ):
        st.divider()

        st.caption(
            f"현재 작업 Case · {saved_inbox_case_id} "
            "· 저장된 검증 결과"
        )

        show_agent_result(
            saved_inbox_state,
            saved_inbox_case_id,
        )


if page == "Case 직접 검증":
    st.divider()

    st.markdown("""
    <div class="aero-section">02 / DEVELOPMENT TOOLS</div>
    <div class="aero-section-title">Case 직접 검증</div>
    """, unsafe_allow_html=True)

    saved_state = st.session_state.get("last_agent_state")
    saved_case_id = st.session_state.get("last_case_id")

    # 기존 결과가 있으면 기본적으로 그대로 유지
    if saved_state and saved_case_id:
        decision = str(
            saved_state.get("decision") or "PROCESSING"
        ).upper()

        st.info(
            f"현재 검증 결과: {saved_case_id} · {decision}"
        )

        if st.button(
            "다른 Case 검증하기",
            key="change_manual_case",
            use_container_width=True,
        ):
            st.session_state["manual_case_edit_mode"] = True
            st.rerun()

    # 결과가 없으면 처음부터 입력 모드
    if not saved_state:
        st.session_state["manual_case_edit_mode"] = True

    edit_mode = st.session_state.get(
        "manual_case_edit_mode",
        False,
    )

    if edit_mode:
        st.caption(
            "Case ID를 직접 입력하여 Agent 품질검증을 실행합니다."
        )

        left, right = st.columns([3, 1])

        with left:
            manual_case_id = st.text_input(
                "Case ID",
                value=saved_case_id or "CASE-001",
                label_visibility="collapsed",
                placeholder="Case ID 입력",
                key="manual_case_id_input",
            )

        with right:
            run_button = st.button(
                "품질검증 실행",
                use_container_width=True,
                type="primary",
                key="manual_run_case",
            )

        if saved_state and saved_case_id:
            if st.button(
                "취소하고 현재 결과로 돌아가기",
                key="cancel_manual_case_change",
            ):
                st.session_state[
                    "manual_case_edit_mode"
                ] = False
                st.rerun()

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
                st.session_state[
                    "manual_case_edit_mode"
                ] = False

                st.rerun()

            except Exception as error:
                st.error(
                    f"Case 실행 중 오류가 발생했습니다: {error}"
                )

    # 저장된 결과는 메뉴 이동/Streamlit rerun 후에도 유지
    saved_state = st.session_state.get(
        "last_agent_state"
    )
    saved_case_id = st.session_state.get(
        "last_case_id"
    )

    if saved_state and saved_case_id:
        st.divider()
        show_agent_result(
            saved_state,
            saved_case_id,
        )

