from tools.quality_data import (
    get_case_id,
    get_drawing_pair,
    get_characteristic,
)


CHANGE_TYPE_MAP = {
    "revision":
        "REVISION_CHANGE",

    "diameter":
        "DIMENSION_CHANGE",

    "tolerance":
        "TOLERANCE_CHANGE",

    "material":
        "MATERIAL_CHANGE",

    "heat_treatment":
        "HEAT_TREATMENT_CHANGE",
}


def analyze_design_change(
    case_data,
    case_id=None
):
    resolved_case_id = (
        case_id
        or get_case_id(
            case_data
        )
    )

    old_drawing, new_drawing = (
        get_drawing_pair(
            case_data
        )
    )

    if (
        old_drawing is None
        or new_drawing is None
    ):
        return {
            "status": "success",
            "case_id":
                resolved_case_id,

            "result": {
                "changes": [],
                "change_types": [],
                "requirements": {}
            },

            "evidence": [],

            "missing_items": [
                {
                    "document_type":
                        "DRAWING",

                    "reason":
                        "변경 전후 도면 부족"
                }
            ]
        }

    old_data = (
        old_drawing[
            "structured_data"
        ]
    )

    new_data = (
        new_drawing[
            "structured_data"
        ]
    )

    old_char = (
        get_characteristic(
            old_data
        )
    )

    new_char = (
        get_characteristic(
            new_data
        )
    )

    changes = []


    def compare(
        item,
        old_value,
        new_value
    ):
        if old_value != new_value:
            changes.append({
                "item":
                    item,

                "old":
                    old_value,

                "new":
                    new_value
            })


    compare(
        "revision",
        old_data.get(
            "revision"
        ),
        new_data.get(
            "revision"
        )
    )

    compare(
        "material",
        old_data.get(
            "material"
        ),
        new_data.get(
            "material"
        )
    )

    compare(
        "heat_treatment",
        old_data.get(
            "heat_treatment"
        ),
        new_data.get(
            "heat_treatment"
        )
    )

    compare(
        "diameter",
        old_char.get(
            "nominal_mm"
        ),
        new_char.get(
            "nominal_mm"
        )
    )

    compare(
        "tolerance",
        old_char.get(
            "tolerance_mm"
        ),
        new_char.get(
            "tolerance_mm"
        )
    )


    change_types = [
        CHANGE_TYPE_MAP[
            change["item"]
        ]
        for change in changes
    ]


    requirements = {
        "revision":
            new_data.get(
                "revision"
            ),

        "material":
            new_data.get(
                "material"
            ),

        "heat_treatment":
            new_data.get(
                "heat_treatment"
            ),

        "nominal_mm":
            new_char.get(
                "nominal_mm"
            ),

        "tolerance_mm":
            new_char.get(
                "tolerance_mm"
            )
    }


    evidence = [
        {
            "role":
                "OLD_DRAWING",

            "file_name":
                old_drawing.get(
                    "file_name"
                ),

            "revision":
                old_data.get(
                    "revision"
                )
        },
        {
            "role":
                "NEW_DRAWING",

            "file_name":
                new_drawing.get(
                    "file_name"
                ),

            "revision":
                new_data.get(
                    "revision"
                )
        }
    ]


    return {
        "status": "success",
        "case_id":
            resolved_case_id,

        "result": {
            "changes":
                changes,

            "change_types":
                change_types,

            "requirements":
                requirements
        },

        "evidence":
            evidence,

        "missing_items": []
    }