from agent.state import create_initial_state


def run_mock_case(case_id: str):
    """실제 Tool 연결 전 테스트용 Case 실행 함수"""

    state = create_initial_state(case_id)

    # 1. 설계변경 분석
    design_change_result = {
        "status": "success",
        "changes": [
            {
                "item": "Material",
                "before": "AL6061-T6",
                "after": "AL7075-T6"
            },
            {
                "item": "Tolerance",
                "before": "±0.2 mm",
                "after": "±0.1 mm"
            }
        ]
    }

    state["design_change_analyzed"] = True
    state["tool_results"]["design_change"] = design_change_result
    state["history"].append("설계변경 분석 완료")

    # 2. 검증계획 생성
    validation_plan_result = {
        "status": "success",
        "tasks": [
            "소재성적서 확인",
            "치수 검사결과 확인"
        ]
    }

    state["validation_plan_created"] = True
    state["tool_results"]["validation_plan"] = validation_plan_result
    state["history"].append("검증계획 생성 완료")

    # 3. 영향범위 추적
    impact_result = {
        "status": "success",
        "affected_lots": [
            "LOT-002",
            "LOT-003",
            "LOT-004"
        ]
    }

    state["impact_traced"] = True
    state["tool_results"]["impact"] = impact_result
    state["history"].append("영향범위 추적 완료")

    # 4. 품질검증
    quality_result = {
        "status": "success",
        "decision": "HOLD",
        "missing_items": [
            "LOT-004 검사성적서"
        ],
        "evidence": [
            {
                "lot_id": "LOT-003",
                "requirement": "AL7075-T6",
                "actual": "AL6061-T6",
                "source": "Material Certificate"
            }
        ]
    }

    state["quality_validated"] = True
    state["decision"] = quality_result["decision"]
    state["missing_items"] = quality_result["missing_items"]
    state["evidence"] = quality_result["evidence"]
    state["tool_results"]["quality"] = quality_result
    state["history"].append("품질검증 완료")

    return state