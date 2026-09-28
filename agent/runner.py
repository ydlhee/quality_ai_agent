from agent.state import create_initial_state

from tools.drawing_compare import analyze_design_change
from tools.verification_plan import create_validation_plan
from tools.lot_trace import trace_impact
from tools.quality_verify import validate_quality
from tools.followup import handle_followup


def run_case(case_id: str):
    """5개 실제 품질검증 Tool을 순차 실행한다."""

    state = create_initial_state(case_id)

    # 1. 설계변경 분석
    design_result = analyze_design_change(
        "data/rev_b.json",
        "data/rev_c.json",
        case_id
    )

    state["design_change_analyzed"] = True
    state["tool_results"]["design_change"] = design_result
    state["history"].append("설계변경 분석 완료")

    # 2. 검증계획 생성
    changes = design_result["result"]["changes"]

    plan_result = create_validation_plan(
        changes,
        case_id
    )

    state["validation_plan_created"] = True
    state["tool_results"]["validation_plan"] = plan_result
    state["history"].append("검증계획 생성 완료")

    # 3. 영향범위 추적
    impact_result = trace_impact(
        "data/lot.csv",
        "A1001",
        "B",
        case_id
    )

    state["impact_traced"] = True
    state["tool_results"]["impact"] = impact_result
    state["history"].append("영향범위 추적 완료")

    affected_lots = [
        lot["lot_id"]
        for lot in impact_result["result"]["affected_lots"]
    ]

    # 4. 품질검증
    quality_result = validate_quality(
        "data/inspection.csv",
        affected_lots,
        20.0,
        0.1,
        case_id
    )

    state["quality_validated"] = True
    state["tool_results"]["quality"] = quality_result

    state["evidence"] = quality_result.get("evidence", [])
    state["missing_items"] = quality_result.get("missing_items", [])

    # Lot별 판정에서 전체 Case 판정 결정
    lot_results = quality_result["result"]["lot_results"]

    decisions = [
        lot["decision"]
        for lot in lot_results
    ]

    if "REJECT" in decisions:
        state["decision"] = "REJECT"
    elif "HOLD" in decisions:
        state["decision"] = "HOLD"
    else:
        state["decision"] = "PASS"

    state["history"].append("품질검증 완료")

    # 5. 후속조치
    followup_result = handle_followup(
        quality_result,
        case_id
    )

    state["followup_completed"] = True
    state["tool_results"]["followup"] = followup_result
    state["history"].append("후속조치 생성 완료")

    return state