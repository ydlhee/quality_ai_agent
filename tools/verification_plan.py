def create_validation_plan(changes, case_id):

    tasks = []

    for change in changes:

        item = change["item"]

        if item == "tolerance":
            tasks.append({
                "type": "dimension_check",
                "required_document": "inspection_report",
                "description": "변경된 공차 기준으로 치수 측정값 확인"
            })

        elif item == "material":
            tasks.append({
                "type": "material_check",
                "required_document": "material_certificate",
                "description": "변경된 재질과 소재성적서 확인"
            })

        elif item == "heat_treatment":
            tasks.append({
                "type": "heat_treatment_check",
                "required_document": "heat_treatment_certificate",
                "description": "변경된 열처리 조건과 열처리성적서 확인"
            })

        elif item == "revision":
            tasks.append({
                "type": "revision_check",
                "required_document": "submitted_document",
                "description": "제출 문서의 Revision 확인"
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