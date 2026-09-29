AVAILABLE_TOOLS = {
    "design_change": "설계변경 분석",
    "validation_plan": "검증계획 생성",
    "impact_trace": "영향범위 추적",
    "validate_quality": "품질검증 및 Risk 판단",
    "followup": "후속조치",
}


def decide_next_tool(state):
    """
    현재 Case 상태를 확인하여 다음에 실행할 Tool 또는 상태를 결정한다.

    PASS:
        품질검증 완료 후 Case 종료

    HOLD:
        보완요청 생성 후 보완자료 수신 대기

    REJECT:
        SCAR 등 후속조치 생성 후 시정조치 자료 수신 대기
    """

    # 1. 설계변경 분석
    if not state["design_change_analyzed"]:
        return {
            "tool": "design_change",
            "reason": "설계변경 분석이 아직 수행되지 않았습니다."
        }

    # 2. 검증계획 생성
    if not state["validation_plan_created"]:
        return {
            "tool": "validation_plan",
            "reason": "설계변경 분석이 완료되어 검증계획 생성이 필요합니다."
        }

    # 3. 영향범위 추적
    if not state["impact_traced"]:
        return {
            "tool": "impact_trace",
            "reason": "검증계획이 생성되어 변경 영향범위 확인이 필요합니다."
        }

    # 4. 품질검증
    if not state["quality_validated"]:
        return {
            "tool": "validate_quality",
            "reason": "영향 대상 Lot이 확인되어 품질검증이 필요합니다."
        }

    # 5. HOLD / REJECT 발생 시 후속조치
    if (
        state["decision"] in ["HOLD", "REJECT"]
        and not state["followup_completed"]
    ):
        return {
            "tool": "followup",
            "reason": (
                f"품질검증 결과가 {state['decision']}이므로 "
                "후속조치가 필요합니다."
            )
        }

    # 6. HOLD 후 보완자료 대기
    if (
        state["decision"] == "HOLD"
        and state["followup_completed"]
    ):
        return {
            "tool": "wait",
            "reason": (
                "보완요청이 생성되었습니다. "
                "협력사의 보완자료 수신을 기다립니다."
            )
        }

    # 7. REJECT 후 시정조치 자료 대기
    if (
        state["decision"] == "REJECT"
        and state["followup_completed"]
    ):
        return {
            "tool": "wait",
            "reason": (
                "부적합 후속조치가 생성되었습니다. "
                "협력사의 시정조치 자료 수신을 기다립니다."
            )
        }

    # 8. PASS인 경우 Case 종료
    return {
        "tool": "finish",
        "reason": "품질검증 결과가 PASS이므로 Case를 종료합니다."
    }