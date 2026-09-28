def create_initial_state(case_id: str):
    """새 품질검증 Case의 초기 상태를 생성한다."""

    return {
        "case_id": case_id,

        "design_change_analyzed": False,
        "validation_plan_created": False,
        "impact_traced": False,
        "quality_validated": False,
        "followup_completed": False,

        "decision": None,
        "missing_items": [],
        "evidence": [],

        "tool_results": {},
        "history": []
    }