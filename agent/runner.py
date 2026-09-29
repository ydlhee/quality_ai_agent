from agent.state import create_initial_state
from agent.agent import decide_next_tool

from tools.drawing_compare import analyze_design_change
from tools.verification_plan import create_validation_plan
from tools.lot_trace import trace_impact
from tools.quality_verify import validate_quality
from tools.followup import handle_followup

from database.case_repository import (
    get_case,
    update_case_status,
)


def _get_quality_decision(result):
    """
    품질검증 결과에서 Case의 최종 품질 판정을 계산한다.

    우선순위:
    REJECT > HOLD > PASS

    Lot 결과가 없는 비정상 상황은 안전하게 HOLD로 처리한다.
    """

    lot_results = (
        result
        .get("result", {})
        .get("lot_results", [])
    )

    decisions = [
        lot.get("decision")
        for lot in lot_results
        if lot.get("decision")
    ]

    if "REJECT" in decisions:
        return "REJECT"

    if "HOLD" in decisions:
        return "HOLD"

    if decisions:
        return "PASS"

    return "HOLD"


def _save_case_status(state, case_status):
    """
    Agent의 메모리 상태와 DB의 Case 상태를 동시에 갱신한다.

    상태 변경을 한 함수에서 처리하여
    메모리와 DB의 상태 불일치를 방지한다.
    """

    state["case_status"] = case_status

    update_case_status(
        state["case_id"],
        case_status,
    )


def run_case(case_id: str):
    """
    새로운 Case의 최초 품질검증 프로세스를 실행한다.

    기본 흐름:
    설계변경 분석
    -> 검증계획 생성
    -> 영향범위 추적
    -> 품질검증 및 Risk 판단
    -> 필요 시 후속조치
    -> 종료 또는 대기

    PASS:
        품질검증 완료 후 Case 종료

    HOLD:
        보완요청 생성 후 보완자료 수신 대기

    REJECT:
        SCAR 등 후속조치 생성 후 시정조치 자료 수신 대기
    """

    state = create_initial_state(case_id)
    case_data = get_case(case_id)

    if case_data is None:
        raise ValueError(
            f"Case를 찾을 수 없습니다: {case_id}"
        )

    while True:
        decision = decide_next_tool(state)

        tool_name = decision["tool"]
        reason = decision["reason"]

        # ====================================================
        # PASS 후 모든 작업이 완료된 경우
        # ====================================================

        if tool_name == "finish":

            _save_case_status(
                state,
                "COMPLETED",
            )

            state["agent_trace"].append({
                "step": len(state["agent_trace"]) + 1,
                "tool": "finish",
                "reason": reason,
                "result": "COMPLETED",
            })

            state["history"].append(
                f"Agent 선택: finish | "
                f"이유: {reason} | "
                f"상태: COMPLETED"
            )

            break

        # ====================================================
        # HOLD / REJECT 후 자료를 기다리는 경우
        # ====================================================

        if tool_name == "wait":

            if state["decision"] == "HOLD":
                wait_status = "WAITING_FOR_CORRECTION"

            elif state["decision"] == "REJECT":
                wait_status = "WAITING_FOR_CORRECTIVE_ACTION"

            else:
                wait_status = "WAITING"

            _save_case_status(
                state,
                wait_status,
            )

            state["revalidation_required"] = True

            state["agent_trace"].append({
                "step": len(state["agent_trace"]) + 1,
                "tool": "wait",
                "reason": reason,
                "result": wait_status,
            })

            state["history"].append(
                f"Agent 선택: wait | "
                f"이유: {reason} | "
                f"상태: {wait_status}"
            )

            break

        # ====================================================
        # 1. 설계변경 분석
        # ====================================================

        if tool_name == "design_change":

            result = analyze_design_change(
                case_data,
                case_id,
            )

            state["design_change_analyzed"] = True
            state["tool_results"]["design_change"] = result

            execution_result = result.get(
                "status",
                "success",
            )

        # ====================================================
        # 2. 검증계획 생성
        # ====================================================

        elif tool_name == "validation_plan":

            changes = (
                state["tool_results"]
                ["design_change"]
                ["result"]
                ["changes"]
            )

            result = create_validation_plan(
                changes,
                case_id,
            )

            state["validation_plan_created"] = True
            state["tool_results"]["validation_plan"] = result

            execution_result = result.get(
                "status",
                "success",
            )

        # ====================================================
        # 3. 영향범위 추적
        # ====================================================

        elif tool_name == "impact_trace":

            result = trace_impact(
                case_data,
                case_id,
            )

            state["impact_traced"] = True
            state["tool_results"]["impact"] = result

            execution_result = result.get(
                "status",
                "success",
            )

        # ====================================================
        # 4. 품질검증 및 Risk 판단
        # ====================================================

        elif tool_name == "validate_quality":

            impact_result = state["tool_results"]["impact"]

            affected_lots = (
                impact_result
                .get("result", {})
                .get("affected_lots", [])
            )

            result = validate_quality(
                case_data,
                affected_lots,
                case_id,
            )

            state["quality_validated"] = True
            state["tool_results"]["quality"] = result

            state["evidence"] = result.get(
                "evidence",
                [],
            )

            state["missing_items"] = result.get(
                "missing_items",
                [],
            )

            state["decision"] = _get_quality_decision(
                result
            )

            execution_result = state["decision"]

        # ====================================================
        # 5. HOLD / REJECT 후속조치
        # ====================================================

        elif tool_name == "followup":

            quality_result = state["tool_results"]["quality"]

            result = handle_followup(
                quality_result,
                case_id,
            )

            state["followup_completed"] = True
            state["tool_results"]["followup"] = result

            execution_result = result.get(
                "status",
                "success",
            )

        else:
            raise ValueError(
                f"알 수 없는 Tool이 선택되었습니다: {tool_name}"
            )

        # ====================================================
        # Tool 실행 기록
        # ====================================================

        state["agent_trace"].append({
            "step": len(state["agent_trace"]) + 1,
            "tool": tool_name,
            "reason": reason,
            "result": execution_result,
        })

        state["history"].append(
            f"Agent 선택: {tool_name} | "
            f"이유: {reason} | "
            f"결과: {execution_result}"
        )

    return state


def revalidate_case(state):
    """
    HOLD 또는 REJECT 상태에서 새로운 보완자료 또는
    시정조치 자료가 수신된 경우 기존 Case를 재검증한다.

    최초 단계에서 이미 완료한
    설계변경 분석, 검증계획 생성, 영향범위 추적은 재사용하고
    품질검증부터 다시 수행한다.
    """

    case_id = state["case_id"]

    if not state.get("revalidation_required"):
        raise ValueError(
            "현재 Case는 재검증 대기 상태가 아닙니다."
        )

    if state.get("case_status") not in [
        "WAITING_FOR_CORRECTION",
        "WAITING_FOR_CORRECTIVE_ACTION",
    ]:
        raise ValueError(
            "현재 Case 상태에서는 재검증을 수행할 수 없습니다."
        )

    # ========================================================
    # 최신 Case 데이터 다시 조회
    # ========================================================

    case_data = get_case(case_id)

    if case_data is None:
        raise ValueError(
            f"Case를 찾을 수 없습니다: {case_id}"
        )

    # ========================================================
    # 재검증 시작 상태 저장
    # ========================================================

    _save_case_status(
        state,
        "REVALIDATING",
    )

    state["revalidation_count"] += 1

    state["history"].append(
        f"재검증 #{state['revalidation_count']} 시작 | "
        f"최신 보완자료를 반영하여 품질검증을 다시 수행합니다."
    )

    # ========================================================
    # 기존 영향범위 결과 재사용
    # ========================================================

    impact_result = state["tool_results"].get(
        "impact",
        {},
    )

    affected_lots = (
        impact_result
        .get("result", {})
        .get("affected_lots", [])
    )

    # ========================================================
    # 품질검증 Tool만 재실행
    # ========================================================

    result = validate_quality(
        case_data,
        affected_lots,
        case_id,
    )

    state["quality_validated"] = True
    state["tool_results"]["quality"] = result

    state["evidence"] = result.get(
        "evidence",
        [],
    )

    state["missing_items"] = result.get(
        "missing_items",
        [],
    )

    state["decision"] = _get_quality_decision(
        result
    )

    state["agent_trace"].append({
        "step": len(state["agent_trace"]) + 1,
        "tool": "validate_quality",
        "reason": (
            "보완자료 또는 시정조치 자료가 수신되어 "
            "관련 품질항목을 재검증합니다."
        ),
        "result": state["decision"],
        "revalidation": state["revalidation_count"],
    })

    state["history"].append(
        f"재검증 #{state['revalidation_count']} | "
        f"결과: {state['decision']}"
    )

    # ========================================================
    # 재검증 결과 PASS
    # ========================================================

    if state["decision"] == "PASS":

        _save_case_status(
            state,
            "COMPLETED",
        )

        state["revalidation_required"] = False
        state["followup_completed"] = True

        state["agent_trace"].append({
            "step": len(state["agent_trace"]) + 1,
            "tool": "finish",
            "reason": (
                "재검증 결과가 PASS이므로 "
                "Case를 종료합니다."
            ),
            "result": "COMPLETED",
        })

        state["history"].append(
            "재검증 결과 PASS | Case 종료"
        )

        return state

    # ========================================================
    # 재검증 결과가 다시 HOLD / REJECT
    # ========================================================

    state["followup_completed"] = False

    followup_result = handle_followup(
        result,
        case_id,
    )

    state["followup_completed"] = True
    state["tool_results"]["followup"] = followup_result

    state["agent_trace"].append({
        "step": len(state["agent_trace"]) + 1,
        "tool": "followup",
        "reason": (
            f"재검증 결과가 {state['decision']}이므로 "
            "추가 후속조치가 필요합니다."
        ),
        "result": followup_result.get(
            "status",
            "success",
        ),
    })

    # ========================================================
    # 다시 대기 상태로 전환
    # ========================================================

    if state["decision"] == "HOLD":
        wait_status = "WAITING_FOR_CORRECTION"

    elif state["decision"] == "REJECT":
        wait_status = "WAITING_FOR_CORRECTIVE_ACTION"

    else:
        wait_status = "WAITING"

    _save_case_status(
        state,
        wait_status,
    )

    state["revalidation_required"] = True

    state["agent_trace"].append({
        "step": len(state["agent_trace"]) + 1,
        "tool": "wait",
        "reason": (
            "재검증 후 추가 조치가 필요하여 "
            "새로운 자료 수신을 기다립니다."
        ),
        "result": wait_status,
    })

    state["history"].append(
        f"재검증 후 대기 | 상태: {wait_status}"
    )

    return state