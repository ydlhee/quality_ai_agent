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


FALLBACK_REQUIREMENTS = {
    "REVISION_CHANGE": {
        "required_document_type":
            "DRAWING",

        "description":
            "변경 전후 도면 Revision 확인"
    },

    "DIMENSION_CHANGE": {
        "required_document_type":
            "INSPECTION_REPORT",

        "description":
            "변경된 치수의 측정결과 확인"
    },

    "TOLERANCE_CHANGE": {
        "required_document_type":
            "INSPECTION_REPORT",

        "description":
            "변경된 공차 기준의 측정결과 확인"
    },

    "MATERIAL_CHANGE": {
        "required_document_type":
            "MATERIAL_CERTIFICATE",

        "description":
            "변경된 재질과 소재성적서 확인"
    },

    "HEAT_TREATMENT_CHANGE": {
        "required_document_type":
            "HEAT_TREATMENT_CERTIFICATE",

        "description":
            "변경된 열처리 조건과 열처리성적서 확인"
    }
}


def _load_requirements(
    change_types
):
    try:
        from database.requirement_repository import (
            get_required_documents
        )

        result = (
            get_required_documents(
                change_types
            )
        )

        if result:
            return result

    except Exception:
        pass


    result = []

    for change_type in change_types:
        rule = (
            FALLBACK_REQUIREMENTS.get(
                change_type
            )
        )

        if rule is None:
            continue

        result.append({
            "change_type":
                change_type,

            "required_document_type":
                rule[
                    "required_document_type"
                ],

            "description":
                rule[
                    "description"
                ]
        })

    return result


def create_validation_plan(
    changes,
    case_id
):
    change_types = []

    for change in changes:
        change_type = (
            CHANGE_TYPE_MAP.get(
                change.get(
                    "item"
                )
            )
        )

        if (
            change_type
            and change_type
            not in change_types
        ):
            change_types.append(
                change_type
            )


    requirements = (
        _load_requirements(
            change_types
        )
    )


    tasks = []

    required_documents = []


    for requirement in requirements:
        document_type = (
            requirement[
                "required_document_type"
            ]
        )

        if (
            document_type
            not in required_documents
        ):
            required_documents.append(
                document_type
            )

        tasks.append({
            "change_type":
                requirement[
                    "change_type"
                ],

            "required_document":
                document_type,

            "description":
                requirement.get(
                    "description",
                    ""
                )
        })


    return {
        "status": "success",
        "case_id":
            case_id,

        "result": {
            "change_types":
                change_types,

            "validation_tasks":
                tasks,

            "required_documents":
                required_documents
        },

        "evidence": [],
        "missing_items": []
    }