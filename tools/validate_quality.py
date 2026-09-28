import csv


def verify_lots(file_path, affected_lots, nominal, tolerance):

    results = []

    with open(file_path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        inspection_data = {
            row["lot_id"]: row
            for row in reader
        }

    for lot_id in affected_lots:

        row = inspection_data.get(lot_id)

        # 검사자료 자체가 없는 경우
        if row is None:
            results.append({
                "lot_id": lot_id,
                "status": "HOLD",
                "reason": "검사자료 없음"
            })
            continue

        # 측정값이 없는 경우
        if row["diameter"] == "":
            results.append({
                "lot_id": lot_id,
                "status": "HOLD",
                "reason": "측정값 없음"
            })
            continue

        measured = float(row["diameter"])

        lower = nominal - tolerance
        upper = nominal + tolerance

        if lower <= measured <= upper:
            status = "PASS"
            reason = "공차 만족"
        else:
            status = "REJECT"
            reason = "공차 초과"

        results.append({
            "lot_id": lot_id,
            "status": status,
            "reason": reason
        })

    return results


def validate_quality(
    file_path,
    affected_lots,
    nominal,
    tolerance,
    case_id
):

    raw_results = verify_lots(
        file_path,
        affected_lots,
        nominal,
        tolerance
    )

    results = []
    evidence = []
    missing_items = []

    for item in raw_results:

        lot_id = item["lot_id"]
        decision = item["status"]
        reason = item["reason"]

        results.append({
            "lot_id": lot_id,
            "decision": decision,
            "reason": reason
        })

        if decision == "HOLD":
            missing_items.append({
                "lot_id": lot_id,
                "reason": reason
            })

        elif decision == "PASS":
            evidence.append({
                "lot_id": lot_id,
                "requirement": f"{nominal} ± {tolerance}",
                "result": "공차 만족"
            })

        elif decision == "REJECT":
            evidence.append({
                "lot_id": lot_id,
                "requirement": f"{nominal} ± {tolerance}",
                "result": "공차 초과"
            })

    return {
        "status": "success",
        "case_id": case_id,
        "result": {
            "lot_results": results
        },
        "evidence": evidence,
        "missing_items": missing_items
    }