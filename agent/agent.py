AVAILABLE_TOOLS = {
    "design_change": "설계변경 분석",
    "validation_plan": "검증계획 생성",
    "impact_trace": "영향범위 추적",
    "validate_quality": "품질검증",
    "followup": "후속조치",
}

def decide_next_tool(state):
    """
    현재 Case 상태를 보고 다음에 실행할 Tool을 결정한다.
    현재는 규칙 기반이며, 이후 LLM Agent 판단으로 교체한다.
    """

    if not state["design_change_analyzed"]:
        return {
            "tool": "design_change",
            "reason": "설계변경 분석이 아직 수행되지 않았습니다."
        }

    if not state["validation_plan_created"]:
        return {
            "tool": "validation_plan",
            "reason": "설계변경 분석이 완료되어 검증계획 생성이 필요합니다."
        }

    if not state["impact_traced"]:
        return {
            "tool": "impact_trace",
            "reason": "검증계획이 생성되어 변경 영향범위 확인이 필요합니다."
        }

    if not state["quality_validated"]:
        return {
            "tool": "validate_quality",
            "reason": "영향 대상 Lot이 확인되어 품질검증이 필요합니다."
        }

    if state["decision"] in ["HOLD", "REJECT"] and not state["followup_completed"]:
        return {
            "tool": "followup",
            "reason": f"품질검증 결과가 {state['decision']}이므로 후속조치가 필요합니다."
        }

    return {
        "tool": "finish",
        "reason": "현재 Case에서 필요한 작업이 모두 완료되었습니다."
    }