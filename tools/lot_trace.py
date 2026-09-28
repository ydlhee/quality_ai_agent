from tools.quality_data import (
    get_case_id,
    get_case_info,
    get_lot,
    parse_date,
)


def trace_impact(
    case_data,
    case_id=None
):
    resolved_case_id = (
        case_id
        or get_case_id(
            case_data
        )
    )

    case_info = (
        get_case_info(
            case_data
        )
    )

    lot = get_lot(
        case_data
    )


    if lot is None:
        return {
            "status": "success",
            "case_id":
                resolved_case_id,

            "result": {
                "affected_lots": [],
                "impact_status":
                    "LOT_NOT_FOUND"
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

    production_date = (
        lot.get(
            "production_date"
        )
    )

    effectivity_date = (
        lot.get(
            "effectivity_date"
        )
    )

    lot_revision = lot.get(
        "revision"
    )

    required_revision = (
        case_info.get(
            "drawing_revision"
        )
    )


    production = parse_date(
        production_date
    )

    effectivity = parse_date(
        effectivity_date
    )


    missing_items = []


    if production is None:
        missing_items.append({
            "item":
                "production_date",

            "reason":
                "Lot 생산일 정보 없음"
        })


    if effectivity is None:
        missing_items.append({
            "item":
                "effectivity_date",

            "reason":
                "Effectivity 정보 없음"
        })


    # Effectivity 판정 불가능 시
    # 안전하게 검증대상에 포함
    if (
        production is None
        or effectivity is None
    ):
        impact_status = (
            "REVIEW_REQUIRED"
        )

        affected = True


    elif production < effectivity:
        impact_status = (
            "BEFORE_EFFECTIVITY"
        )

        affected = False


    else:
        impact_status = (
            "IN_EFFECTIVITY_SCOPE"
        )

        affected = True


    affected_lots = []


    if affected:
        affected_lots.append({
            "lot_id":
                lot_no,

            "lot_no":
                lot_no,

            "part_no":
                lot.get(
                    "part_no"
                ),

            "po_no":
                lot.get(
                    "po_no"
                ),

            "production_date":
                production_date,

            "effectivity_date":
                effectivity_date,

            "revision":
                lot_revision,

            "required_revision":
                required_revision,

            "revision_compliant":
                (
                    lot_revision
                    == required_revision
                    if required_revision
                    is not None
                    else None
                )
        })


    evidence = [
        {
            "lot_no":
                lot_no,

            "production_date":
                production_date,

            "effectivity_date":
                effectivity_date,

            "lot_revision":
                lot_revision,

            "required_revision":
                required_revision,

            "impact_status":
                impact_status
        }
    ]


    return {
        "status": "success",
        "case_id":
            resolved_case_id,

        "result": {
            "affected_lots":
                affected_lots,

            "impact_status":
                impact_status
        },

        "evidence":
            evidence,

        "missing_items":
            missing_items
    }