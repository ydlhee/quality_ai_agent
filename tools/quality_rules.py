def make_result(
    decision,
    issue_code,
    reason,
    requirement,
    actual_value
):
    return {
        "decision":
            decision,

        "issue_code":
            issue_code,

        "reason":
            reason,

        "requirement":
            requirement,

        "actual_value":
            actual_value
    }


def evaluate_quality(
    requirements,
    actual,
    required_documents
):
    required_revision = (
        requirements.get(
            "revision"
        )
    )

    required_material = (
        requirements.get(
            "material"
        )
    )

    required_heat_treatment = (
        requirements.get(
            "heat_treatment"
        )
    )

    nominal = (
        requirements.get(
            "nominal_mm"
        )
    )

    tolerance = (
        requirements.get(
            "tolerance_mm"
        )
    )

    lot_no = actual.get(
        "lot_no"
    )

    lot_revision = actual.get(
        "lot_revision"
    )


    # ==================================
    # 1. Lot Revision
    # ==================================

    if (
        required_revision
        and lot_revision
        and lot_revision
        != required_revision
    ):
        return make_result(
            "REJECT",
            "REVISION_MISMATCH",
            (
                f"Lot Revision 불일치 "
                f"(요구: {required_revision}, "
                f"실제: {lot_revision})"
            ),
            required_revision,
            lot_revision
        )


    # ==================================
    # 2. 검사성적서 Lot 번호
    # ==================================

    inspection_lot_no = (
        actual.get(
            "inspection_lot_no"
        )
    )

    if (
        inspection_lot_no
        and lot_no
        and inspection_lot_no
        != lot_no
    ):
        return make_result(
            "REJECT",
            "LOT_ID_MISMATCH",
            (
                f"Lot 번호 불일치 "
                f"(대상: {lot_no}, "
                f"문서: {inspection_lot_no})"
            ),
            lot_no,
            inspection_lot_no
        )


    # ==================================
    # 3. 검사성적서 Revision
    # ==================================

    inspection_revision = (
        actual.get(
            "inspection_revision"
        )
    )

    if (
        inspection_revision
        and required_revision
        and inspection_revision
        != required_revision
    ):
        return make_result(
            "HOLD",
            "REVISION_MISMATCH",
            (
                f"검사성적서 Revision 불일치 "
                f"(요구: {required_revision}, "
                f"실제: {inspection_revision})"
            ),
            required_revision,
            inspection_revision
        )


    # ==================================
    # 4. Material
    # ==================================

    if (
        "MATERIAL_CERTIFICATE"
        in required_documents
        or required_material
        is not None
    ):
        actual_material = (
            actual.get(
                "material"
            )
        )

        if actual_material is None:
            return make_result(
                "HOLD",
                "MATERIAL_DATA_MISSING",
                "재질 정보 없음",
                required_material,
                None
            )

        if (
            required_material
            and actual_material
            != required_material
        ):
            return make_result(
                "REJECT",
                "MATERIAL_MISMATCH",
                (
                    f"재질 불일치 "
                    f"(요구: {required_material}, "
                    f"실제: {actual_material})"
                ),
                required_material,
                actual_material
            )


    # ==================================
    # 5. Heat Treatment
    # ==================================

    if (
        "HEAT_TREATMENT_CERTIFICATE"
        in required_documents
        or required_heat_treatment
        is not None
    ):
        actual_heat = (
            actual.get(
                "heat_treatment"
            )
        )

        if actual_heat is None:
            return make_result(
                "HOLD",
                "HEAT_TREATMENT_DATA_MISSING",
                "열처리 정보 없음",
                required_heat_treatment,
                None
            )

        if (
            required_heat_treatment
            and actual_heat
            != required_heat_treatment
        ):
            return make_result(
                "REJECT",
                "HEAT_TREATMENT_MISMATCH",
                (
                    f"열처리 조건 불일치 "
                    f"(요구: "
                    f"{required_heat_treatment}, "
                    f"실제: {actual_heat})"
                ),
                required_heat_treatment,
                actual_heat
            )


    # ==================================
    # 6. Heat No. 추적성
    # ==================================

    material_heat_no = (
        actual.get(
            "material_heat_no"
        )
    )

    heat_heat_no = (
        actual.get(
            "heat_heat_no"
        )
    )

    expected_heat_no = requirements.get("expected_heat_no")
    if expected_heat_no:
        missing = [name for name, value in (
            ("소재성적서", material_heat_no),
            ("열처리성적서", heat_heat_no),
        ) if not value]

        mismatched = [name for name, value in (
            ("소재성적서", material_heat_no),
            ("열처리성적서", heat_heat_no),
        ) if value and value != expected_heat_no]

        if mismatched:
            return make_result(
                "HOLD",
                "HEAT_NO_MISMATCH",
                "기준 Heat No. 불일치: " + ", ".join(mismatched),
                expected_heat_no,
                {
                    "material": material_heat_no,
                    "heat_treatment": heat_heat_no,
                },
            )

        if missing:
            return make_result(
                "HOLD",
                "HEAT_NO_MISSING",
                "Heat No. 누락: " + ", ".join(missing),
                expected_heat_no,
                {
                    "material": material_heat_no,
                    "heat_treatment": heat_heat_no,
                },
            )

    elif (
        material_heat_no
        and heat_heat_no
        and material_heat_no != heat_heat_no
    ):
        return make_result(
            "HOLD",
            "HEAT_NO_MISMATCH",
            "성적서 간 Heat No. 불일치",
            material_heat_no,
            heat_heat_no,
        )


    # ==================================
    # 7. 치수 / 공차
    # ==================================

    inspection_required = (
        "INSPECTION_REPORT"
        in required_documents
    )

    measured = actual.get(
        "measured_mm"
    )

    if (
        inspection_required
        and measured is None
    ):
        return make_result(
            "HOLD",
            "MEASUREMENT_MISSING",
            "측정값 없음",
            (
                f"{nominal} ± {tolerance}"
            ),
            None
        )

    if (
        measured is not None
        and nominal is not None
        and tolerance is not None
    ):
        lower = (
            nominal
            - tolerance
        )

        upper = (
            nominal
            + tolerance
        )

        if not (
            lower
            <= measured
            <= upper
        ):
            return make_result(
                "REJECT",
                "DIMENSION_OUT_OF_TOLERANCE",
                (
                    f"공차 초과 "
                    f"(요구: "
                    f"{nominal} ± {tolerance}, "
                    f"실제: {measured})"
                ),
                (
                    f"{nominal} "
                    f"± {tolerance}"
                ),
                measured
            )


    # ==================================
    # PASS
    # ==================================

    return make_result(
        "PASS",
        "NO_ISSUE",
        "모든 품질검증 기준 만족",
        requirements,
        actual
    )