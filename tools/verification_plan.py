def create_validation_plan(
    changes,
    case_id,
    expected_heat_no=None
):

    tasks = []

    for change in changes:

        item = change["item"]

        # Revision 변경
        if item == "revision":
            tasks.append({
                "type": "revision_check",
                "required_document": "submitted_document",
                "description": "제출 문서의 Revision 확인"
            })

        # 공차 변경
        elif item == "tolerance":
            tasks.append({
                "type": "dimension_check",
                "required_document": "inspection_report",
                "description": "변경된 공차 기준으로 치수 측정값 확인"
            })

        # 치수 변경
        elif item == "diameter":
            tasks.append({
                "type": "dimension_check",
                "required_document": "inspection_report",
                "description": "변경된 치수 기준으로 측정값 확인"
            })

        # 재질 변경
        elif item == "material":
            tasks.append({
                "type": "material_check",
                "required_document": "material_certificate",
                "description": "변경된 재질과 소재성적서 확인"
            })

        # 열처리 변경
        elif item == "heat_treatment":
            tasks.append({
                "type": "heat_treatment_check",
                "required_document": "heat_treatment_certificate",
                "description": "변경된 열처리 조건과 열처리성적서 확인"
            })

    # Heat No. 추적이 필요한 Case
    if expected_heat_no is not None:
        tasks.append({
            "type": "heat_no_check",
            "required_document": "material_certificate",
            "description": "요구 Heat No.와 품질문서의 Heat No. 일치 여부 확인"
        })

    return {
        "status": "success",
        "case_id": case_id,
        "result": {
            "validation_tasks": tasks
        },
        "evidence": [],
        "missing_items": []
    }