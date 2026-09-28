import csv


def verify_lots(
    file_path,
    affected_lots,
    nominal,
    tolerance,
    expected_revision=None,
    expected_material=None,
    expected_heat_treatment=None,
    expected_heat_no=None
):

    results = []

    with open(file_path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        inspection_data = {
            row["lot_id"]: row
            for row in reader
        }

    for lot_id in affected_lots:

        row = inspection_data.get(lot_id)

        # ======================================
        # 1. 검사자료 없음
        # ======================================
        if row is None:

            results.append({
                "lot_id": lot_id,
                "status": "HOLD",
                "issue_code": "INSPECTION_DATA_MISSING",
                "reason": "검사자료 없음",
                "requirement": "검사자료 제출",
                "actual_value": None
            })

            continue


        # ======================================
        # 2. Revision 검증
        # ======================================
        if expected_revision is not None:

            document_revision = row.get(
                "document_revision",
                ""
            )

            if document_revision != expected_revision:

                results.append({
                    "lot_id": lot_id,
                    "status": "HOLD",
                    "issue_code": "REVISION_MISMATCH",
                    "reason": (
                        f"문서 Revision 불일치 "
                        f"(요구: {expected_revision}, "
                        f"실제: {document_revision})"
                    ),
                    "requirement": expected_revision,
                    "actual_value": document_revision
                })

                continue


        # ======================================
        # 3. 문서 Lot 번호 검증
        # ======================================
        document_lot_id = row.get(
            "document_lot_id",
            ""
        )

        if (
            document_lot_id != ""
            and document_lot_id != lot_id
        ):

            results.append({
                "lot_id": lot_id,
                "status": "HOLD",
                "issue_code": "LOT_ID_MISMATCH",
                "reason": (
                    f"Lot 번호 불일치 "
                    f"(대상 Lot: {lot_id}, "
                    f"문서 Lot: {document_lot_id})"
                ),
                "requirement": lot_id,
                "actual_value": document_lot_id
            })

            continue


        # ======================================
        # 4. Heat No. 검증
        # ======================================
        if expected_heat_no is not None:

            actual_heat_no = row.get(
                "heat_no",
                ""
            )

            if actual_heat_no == "":

                results.append({
                    "lot_id": lot_id,
                    "status": "HOLD",
                    "issue_code": "HEAT_NO_MISSING",
                    "reason": "Heat No. 정보 없음",
                    "requirement": expected_heat_no,
                    "actual_value": None
                })

                continue

            if actual_heat_no != expected_heat_no:

                results.append({
                    "lot_id": lot_id,
                    "status": "HOLD",
                    "issue_code": "HEAT_NO_MISMATCH",
                    "reason": (
                        f"Heat No. 불일치 "
                        f"(요구: {expected_heat_no}, "
                        f"실제: {actual_heat_no})"
                    ),
                    "requirement": expected_heat_no,
                    "actual_value": actual_heat_no
                })

                continue


        # ======================================
        # 5. 재질 검증
        # ======================================
        if expected_material is not None:

            actual_material = row.get(
                "material",
                ""
            )

            if actual_material == "":

                results.append({
                    "lot_id": lot_id,
                    "status": "HOLD",
                    "issue_code": "MATERIAL_DATA_MISSING",
                    "reason": "재질 정보 없음",
                    "requirement": expected_material,
                    "actual_value": None
                })

                continue

            if actual_material != expected_material:

                results.append({
                    "lot_id": lot_id,
                    "status": "REJECT",
                    "issue_code": "MATERIAL_MISMATCH",
                    "reason": (
                        f"재질 불일치 "
                        f"(요구: {expected_material}, "
                        f"실제: {actual_material})"
                    ),
                    "requirement": expected_material,
                    "actual_value": actual_material
                })

                continue


        # ======================================
        # 6. 열처리 검증
        # ======================================
        if expected_heat_treatment is not None:

            actual_heat_treatment = row.get(
                "heat_treatment",
                ""
            )

            if actual_heat_treatment == "":

                results.append({
                    "lot_id": lot_id,
                    "status": "HOLD",
                    "issue_code": "HEAT_TREATMENT_DATA_MISSING",
                    "reason": "열처리 정보 없음",
                    "requirement": expected_heat_treatment,
                    "actual_value": None
                })

                continue

            if (
                actual_heat_treatment
                != expected_heat_treatment
            ):

                results.append({
                    "lot_id": lot_id,
                    "status": "REJECT",
                    "issue_code": "HEAT_TREATMENT_MISMATCH",
                    "reason": (
                        f"열처리 조건 불일치 "
                        f"(요구: {expected_heat_treatment}, "
                        f"실제: {actual_heat_treatment})"
                    ),
                    "requirement": expected_heat_treatment,
                    "actual_value": actual_heat_treatment
                })

                continue


        # ======================================
        # 7. 측정값 없음
        # ======================================
        if row.get("diameter", "") == "":

            results.append({
                "lot_id": lot_id,
                "status": "HOLD",
                "issue_code": "MEASUREMENT_MISSING",
                "reason": "측정값 없음",
                "requirement": f"{nominal} ± {tolerance}",
                "actual_value": None
            })

            continue


        # ======================================
        # 8. 치수 / 공차 검증
        # ======================================
        measured = float(
            row["diameter"]
        )

        lower = nominal - tolerance
        upper = nominal + tolerance

        if lower <= measured <= upper:

            results.append({
                "lot_id": lot_id,
                "status": "PASS",
                "issue_code": "NO_ISSUE",
                "reason": "공차 만족",
                "requirement": f"{nominal} ± {tolerance}",
                "actual_value": measured
            })

        else:

            results.append({
                "lot_id": lot_id,
                "status": "REJECT",
                "issue_code": "DIMENSION_OUT_OF_TOLERANCE",
                "reason": (
                    f"공차 초과 "
                    f"(요구: {nominal} ± {tolerance}, "
                    f"실제: {measured})"
                ),
                "requirement": f"{nominal} ± {tolerance}",
                "actual_value": measured
            })

    return results


def validate_quality(
    file_path,
    affected_lots,
    nominal,
    tolerance,
    case_id,
    expected_revision=None,
    expected_material=None,
    expected_heat_treatment=None,
    expected_heat_no=None
):

    raw_results = verify_lots(
        file_path,
        affected_lots,
        nominal,
        tolerance,
        expected_revision,
        expected_material,
        expected_heat_treatment,
        expected_heat_no
    )

    results = []
    evidence = []
    missing_items = []

    for item in raw_results:

        lot_id = item["lot_id"]
        decision = item["status"]
        issue_code = item["issue_code"]
        reason = item["reason"]

        requirement = item.get(
            "requirement"
        )

        actual_value = item.get(
            "actual_value"
        )

        results.append({
            "lot_id": lot_id,
            "decision": decision,
            "issue_code": issue_code,
            "reason": reason,
            "requirement": requirement,
            "actual_value": actual_value
        })

        evidence.append({
            "lot_id": lot_id,
            "issue_code": issue_code,
            "requirement": requirement,
            "actual_value": actual_value,
            "decision": decision,
            "reason": reason
        })

        if decision == "HOLD":

            missing_items.append({
                "lot_id": lot_id,
                "issue_code": issue_code,
                "reason": reason
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