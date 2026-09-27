def handle_followup(validation_result, case_id):

    actions = []

    lot_results = validation_result["result"]["lot_results"]

    for item in lot_results:

        lot_id = item["lot_id"]
        decision = item["decision"]

        if decision == "PASS":
            actions.append({
                "lot_id": lot_id,
                "action": "NONE",
                "description": "추가 조치 없음"
            })

        elif decision == "HOLD":
            actions.append({
                "lot_id": lot_id,
                "action": "CORRECTION_REQUEST",
                "description": "누락 또는 오류 자료에 대한 정정 요청"
            })

        elif decision == "REJECT":
            actions.append({
                "lot_id": lot_id,
                "action": "REJECT_LOT",
                "description": "제품 요구조건 미달로 Lot 반품 검토"
            })

    return {
        "status": "success",
        "case_id": case_id,
        "result": {
            "actions": actions
        },
        "evidence": [],
        "missing_items": []
    }