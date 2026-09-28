from agent.state import create_initial_state
from agent.agent import decide_next_tool

from tools.drawing_compare import analyze_design_change
from tools.verification_plan import create_validation_plan
from tools.lot_trace import trace_impact
from tools.validate_quality import validate_quality
from tools.followup import handle_followup


def run_case(case_id: str):
    """Case 상태를 바탕으로 다음 Tool을 판단하고 실행한다."""

    state = create_initial_state(case_id)

    while True:

        # Agent가 현재 상태를 보고 다음 Tool 판단
        decision = decide_next_tool(state)

        tool_name = decision["tool"]
        reason = decision["reason"]

        # 모든 작업이 끝났으면 종료 기록
        if tool_name == "finish":

            state["agent_trace"].append({
                "step": len(state["agent_trace"]) + 1,
                "tool": "finish",
                "reason": reason,
                "result": "completed"
            })

            state["history"].append(
                f"Agent 선택: finish | 이유: {reason}"
            )

            break

        # 1. 설계변경 분석 Tool
        if tool_name == "design_change":

            result = analyze_design_change(
                "data/rev_b.json",
                "data/rev_c.json",
                case_id
            )

            state["design_change_analyzed"] = True
            state["tool_results"]["design_change"] = result

            execution_result = result.get("status", "success")

        # 2. 검증계획 생성 Tool
        elif tool_name == "validation_plan":

            changes = state["tool_results"]["design_change"]["result"]["changes"]

            result = create_validation_plan(
                changes,
                case_id
            )

            state["validation_plan_created"] = True
            state["tool_results"]["validation_plan"] = result

            execution_result = result.get("status", "success")

        # 3. 영향범위 추적 Tool
        elif tool_name == "impact_trace":

            result = trace_impact(
                "data/lot.csv",
                "A1001",
                "B",
                case_id
            )

            state["impact_traced"] = True
            state["tool_results"]["impact"] = result

            execution_result = result.get("status", "success")

        # 4. 품질검증 Tool
        elif tool_name == "validate_quality":

            impact_result = state["tool_results"]["impact"]

            affected_lots = [
                lot["lot_id"]
                for lot in impact_result["result"]["affected_lots"]
            ]

            result = validate_quality(
                "data/inspection.csv",
                affected_lots,
                20.0,
                0.1,
                case_id
            )

            state["quality_validated"] = True
            state["tool_results"]["quality"] = result

            state["evidence"] = result.get("evidence", [])
            state["missing_items"] = result.get("missing_items", [])

            # Lot별 판정을 이용해 Case 전체 판정
            lot_results = result["result"]["lot_results"]

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

            # 품질검증 Tool은 success 대신 실제 품질판정을 기록
            execution_result = state["decision"]

        # 5. 후속조치 Tool
        elif tool_name == "followup":

            quality_result = state["tool_results"]["quality"]

            result = handle_followup(
                quality_result,
                case_id
            )

            state["followup_completed"] = True
            state["tool_results"]["followup"] = result

            execution_result = result.get("status", "success")

        else:
            raise ValueError(
                f"알 수 없는 Tool이 선택되었습니다: {tool_name}"
            )

        # Agent가 Tool을 선택한 이유 + 실제 실행 결과 기록
        state["agent_trace"].append({
            "step": len(state["agent_trace"]) + 1,
            "tool": tool_name,
            "reason": reason,
            "result": execution_result
        })

        state["history"].append(
            f"Agent 선택: {tool_name} | 이유: {reason} | 결과: {execution_result}"
        )

    return state