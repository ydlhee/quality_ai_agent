from agent.state import create_initial_state
from agent.agent import decide_next_tool

from tools.drawing_compare import analyze_design_change
from tools.verification_plan import create_validation_plan
from tools.lot_trace import trace_impact
from tools.quality_verify import validate_quality
from tools.followup import handle_followup

from database.case_repository import get_case, update_case_status


def _get_quality_decision(result):
    """Lot 판정 우선순위: REJECT > HOLD > PASS. 결과가 없으면 HOLD."""
    lot_results = result.get("result", {}).get("lot_results", [])
    decisions = [lot.get("decision") for lot in lot_results if lot.get("decision")]
    if "REJECT" in decisions:
        return "REJECT"
    if "HOLD" in decisions:
        return "HOLD"
    return "PASS" if decisions else "HOLD"


def _save_case_status(state, case_status):
    state["case_status"] = case_status
    update_case_status(state["case_id"], case_status)


def _record_trace(state, tool, reason, result, source, revalidation=None):
    """실행 이력에 판단 출처를 보존한다."""
    entry = {
        "step": len(state["agent_trace"]) + 1,
        "tool": tool,
        "reason": reason,
        "result": result,
        "decision_source": source,
    }
    if revalidation is not None:
        entry["revalidation"] = revalidation
    state["agent_trace"].append(entry)
    state["history"].append(
        f"Agent 선택: {tool} | 판단 출처: {source} | "
        f"이유: {reason} | 결과: {result}"
    )


def run_case(case_id: str):
    """Case의 전체 검증 프로세스를 실행한다."""
    state = create_initial_state(case_id)
    case_data = get_case(case_id)
    if case_data is None:
        raise ValueError(f"Case를 찾을 수 없습니다: {case_id}")

    while True:
        decision = decide_next_tool(state)
        tool_name = decision["tool"]
        reason = decision["reason"]
        source = decision.get("decision_source", "UNKNOWN")

        if tool_name == "finish":
            _save_case_status(state, "COMPLETED")
            _record_trace(state, "finish", reason, "COMPLETED", source)
            break

        if tool_name == "wait":
            if state["decision"] == "HOLD":
                wait_status = "WAITING_FOR_CORRECTION"
            elif state["decision"] == "REJECT":
                wait_status = "WAITING_FOR_CORRECTIVE_ACTION"
            else:
                wait_status = "WAITING"
            _save_case_status(state, wait_status)
            state["revalidation_required"] = True
            _record_trace(state, "wait", reason, wait_status, source)
            break

        if tool_name == "design_change":
            result = analyze_design_change(case_data, case_id)
            state["design_change_analyzed"] = True
            state["tool_results"]["design_change"] = result
            execution_result = result.get("status", "success")

        elif tool_name == "validation_plan":
            changes = state["tool_results"]["design_change"]["result"]["changes"]
            result = create_validation_plan(changes, case_id)
            state["validation_plan_created"] = True
            state["tool_results"]["validation_plan"] = result
            execution_result = result.get("status", "success")

        elif tool_name == "impact_trace":
            result = trace_impact(case_data, case_id)
            state["impact_traced"] = True
            state["tool_results"]["impact"] = result
            execution_result = result.get("status", "success")

        elif tool_name == "validate_quality":
            impact_result = state["tool_results"]["impact"]
            affected_lots = impact_result.get("result", {}).get("affected_lots", [])
            result = validate_quality(case_data, affected_lots, case_id)
            state["quality_validated"] = True
            state["tool_results"]["quality"] = result
            state["evidence"] = result.get("evidence", [])
            state["missing_items"] = result.get("missing_items", [])
            state["decision"] = _get_quality_decision(result)
            execution_result = state["decision"]

        elif tool_name == "followup":
            quality_result = state["tool_results"]["quality"]
            result = handle_followup(quality_result, case_id)
            state["followup_completed"] = True
            state["tool_results"]["followup"] = result
            execution_result = result.get("status", "success")

        else:
            raise ValueError(f"알 수 없는 Tool이 선택되었습니다: {tool_name}")

        _record_trace(state, tool_name, reason, execution_result, source)

    return state


def revalidate_case(state):
    """보완자료 수신 후 기존 영향범위를 재사용하여 품질검증을 재실행한다."""
    case_id = state["case_id"]
    if not state.get("revalidation_required"):
        raise ValueError("현재 Case는 재검증 대기 상태가 아닙니다.")
    if state.get("case_status") not in [
        "WAITING_FOR_CORRECTION", "WAITING_FOR_CORRECTIVE_ACTION"
    ]:
        raise ValueError("현재 Case 상태에서는 재검증을 수행할 수 없습니다.")

    case_data = get_case(case_id)
    if case_data is None:
        raise ValueError(f"Case를 찾을 수 없습니다: {case_id}")

    _save_case_status(state, "REVALIDATING")
    state["revalidation_count"] += 1
    state["history"].append(
        f"재검증 #{state['revalidation_count']} 시작 | "
        "최신 보완자료를 반영하여 품질검증을 다시 수행합니다."
    )

    impact_result = state["tool_results"].get("impact", {})
    affected_lots = impact_result.get("result", {}).get("affected_lots", [])
    result = validate_quality(case_data, affected_lots, case_id)
    state["quality_validated"] = True
    state["tool_results"]["quality"] = result
    state["evidence"] = result.get("evidence", [])
    state["missing_items"] = result.get("missing_items", [])
    state["decision"] = _get_quality_decision(result)
    _record_trace(
        state, "validate_quality",
        "보완자료 또는 시정조치 자료가 수신되어 관련 품질항목을 재검증합니다.",
        state["decision"], "RULE", state["revalidation_count"]
    )

    if state["decision"] == "PASS":
        _save_case_status(state, "COMPLETED")
        state["revalidation_required"] = False
        state["followup_completed"] = True
        _record_trace(
            state, "finish", "재검증 결과가 PASS이므로 Case를 종료합니다.",
            "COMPLETED", "RULE"
        )
        return state

    state["followup_completed"] = False
    followup_result = handle_followup(result, case_id)
    state["followup_completed"] = True
    state["tool_results"]["followup"] = followup_result
    _record_trace(
        state, "followup",
        f"재검증 결과가 {state['decision']}이므로 추가 후속조치가 필요합니다.",
        followup_result.get("status", "success"), "RULE"
    )

    if state["decision"] == "HOLD":
        wait_status = "WAITING_FOR_CORRECTION"
    elif state["decision"] == "REJECT":
        wait_status = "WAITING_FOR_CORRECTIVE_ACTION"
    else:
        wait_status = "WAITING"
    _save_case_status(state, wait_status)
    state["revalidation_required"] = True
    _record_trace(
        state, "wait", "재검증 후 추가 조치가 필요하여 새로운 자료 수신을 기다립니다.",
        wait_status, "RULE"
    )
    return state
