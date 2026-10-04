def create_initial_state(case_id: str):
    """품질검증 Case의 초기 Agent 상태를 생성한다."""

    return {
        "case_id": case_id,

        # Tool 수행 여부
        "design_change_analyzed": False,
        "validation_plan_created": False,
        "impact_traced": False,
        "quality_validated": False,
        "followup_completed": False,

        # Case 진행 상태
        "case_status": "PROCESSING",
        "decision": None,

        # 재검증 관련 상태
        "revalidation_required": False,
        "revalidation_count": 0,

        # 검증 결과
        "missing_items": [],
        "evidence": [],

        # 자율 판단 및 검증계획 조정 상태
        "agent_phase": "INITIAL",
        "plan_review_completed": False,
        "additional_checks": [],
        "pending_actions": [],
        "plan_adjustments": [],
        
        # 동적 계획 및 자율적 실행 관리
        "execution_plan": [],
        "completed_actions": [],
        "plan_revision": 0,
        "replanning_required": False,
        "replanning_reason": None,

        # Tool 실행 결과 및 Agent 기록
        "tool_results": {},
        "history": [],
        "agent_trace": []
    }
