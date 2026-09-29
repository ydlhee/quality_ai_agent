from tools.drawing_compare import (
    analyze_design_change,
)

from tools.verification_plan import (
    create_validation_plan,
)

from tools.quality_data import (
    get_case_id,
    get_lot,
    extract_requirements,
    extract_actual_values,
    get_received_document_types,
    normalize_required_documents,
)

from tools.quality_rules import (
    evaluate_quality,
)


def _extract_target_lots(
    affected_lots,
    default_lot_no
):
    if affected_lots is None:
        return [
            default_lot_no
        ]

    result = []

    for item in affected_lots:

        if isinstance(item, dict):
            lot_no = (
                item.get(
                    "lot_no"
                )
                or item.get(
                    "lot_id"
                )
            )

        else:
            lot_no = item

        if lot_no:
            result.append(
                lot_no
            )

    return result


def validate_quality(
    case_data,
    affected_lots=None,
    case_id=None,
    required_documents=None
):
    resolved_case_id = (
        case_id
        or get_case_id(
            case_data
        )
    )

    lot = get_lot(
        case_data
    )


    # ==================================
    # Lot 정보 없음
    # ==================================

    if lot is None:
        return {
            "status": "success",
            "case_id":
                resolved_case_id,

            "result": {
                "lot_results": []
            },

            "evidence": [],

            "missing_items": [
                {
                    "item": "LOT",
                    "reason":
                        "Case에 연결된 Lot 정보 없음"
                }
            ]
        }


    lot_no = lot.get(
        "lot_no"
    )


    target_lots = (
        _extract_target_lots(
            affected_lots,
            lot_no
        )
    )


    # Effectivity 범위 밖
    if lot_no not in target_lots:
        return {
            "status": "success",
            "case_id":
                resolved_case_id,

            "result": {
                "lot_results": []
            },

            "evidence": [],

            "missing_items": []
        }


    # ==================================
    # 설계변경 분석
    # ==================================

    design_result = (
        analyze_design_change(
            case_data,
            resolved_case_id
        )
    )

    changes = (
        design_result[
            "result"
        ].get(
            "changes",
            []
        )
    )


    requirements = (
        design_result[
            "result"
        ].get(
            "requirements"
        )
    )


    # 혹시 drawing_compare에서
    # requirements를 못 만든 경우
    if not requirements:
        (
            requirements,
            requirement_evidence
        ) = extract_requirements(
            case_data
        )
    else:
        requirement_evidence = (
            design_result.get(
                "evidence",
                []
            )
        )


    # ==================================
    # 검증계획 / 필수문서
    # ==================================

    plan_result = (
        create_validation_plan(
            changes,
            resolved_case_id
        )
    )


    if required_documents is None:
        required_documents = (
            plan_result[
                "result"
            ].get(
                "required_documents",
                []
            )
        )


    required_documents = (
        normalize_required_documents(
            required_documents
        )
    )


    received_documents = (
        get_received_document_types(
            case_data
        )
    )


    missing_documents = [
        document_type
        for document_type
        in required_documents
        if document_type
        not in received_documents
    ]


    # ==================================
    # 필수문서 누락 → HOLD
    # ==================================

    if missing_documents:

        reason = (
            "필수 품질문서 누락: "
            + ", ".join(
                missing_documents
            )
        )

        lot_result = {
            "lot_id":
                lot_no,

            "decision":
                "HOLD",

            "issue_code":
                "REQUIRED_DOCUMENT_MISSING",

            "reason":
                reason,

            "requirement":
                missing_documents,

            "actual_value":
                sorted(
                    received_documents
                )
        }


        missing_items = [
            {
                "lot_id":
                    lot_no,

                "issue_code":
                    "REQUIRED_DOCUMENT_MISSING",

                "document_type":
                    document_type,

                "reason":
                    f"{document_type} 누락"
            }
            for document_type
            in missing_documents
        ]

        evidence = [
            {
                **item,
                "lot_id": lot_no,
                "requirement": lot_result["requirement"],
                "actual_value": lot_result["actual_value"],
                "result": lot_result["decision"]
            }
            for item in requirement_evidence
        ]
        return {
            "status": "success",
            "case_id":
                resolved_case_id,

            "result": {
                "lot_results": [
                    lot_result
                ],

                "required_documents":
                    required_documents
            },

            "evidence":
                evidence,

            "missing_items":
                missing_items
        }


    # ==================================
    # 실제 품질 데이터 추출
    # ==================================

    actual, actual_evidence = (
        extract_actual_values(
            case_data
        )
    )


    # ==================================
    # Rule 기반 품질판정
    # ==================================

    rule_result = (
        evaluate_quality(
            requirements,
            actual,
            required_documents
        )
    )


    lot_result = {
        "lot_id":
            lot_no,

        "decision":
            rule_result[
                "decision"
            ],

        "issue_code":
            rule_result[
                "issue_code"
            ],

        "reason":
            rule_result[
                "reason"
            ],

        "requirement":
            rule_result[
                "requirement"
            ],

        "actual_value":
            rule_result[
                "actual_value"
            ]
    }


    missing_items = []


    if (
        rule_result[
            "decision"
        ]
        == "HOLD"
    ):
        missing_items.append({
            "lot_id":
                lot_no,

            "issue_code":
                rule_result[
                    "issue_code"
                ],

            "reason":
                rule_result[
                    "reason"
                ]
        })


    evidence = (
        requirement_evidence
        + actual_evidence
    )
    evidence = [
        {
            **item,
            "lot_id": lot_no,
            "requirement": lot_result["requirement"],
            "actual_value": lot_result["actual_value"],
            "result": lot_result["decision"]
        }
        for item in evidence
    ]


    return {
        "status": "success",
        "case_id":
            resolved_case_id,

        "result": {
            "lot_results": [
                lot_result
            ],

            "requirements":
                requirements,

            "required_documents":
                required_documents
        },

        "evidence":
            evidence,

        "missing_items":
            missing_items
    }