from datetime import datetime


def get_case_id(case_data):
    return (
        case_data.get("case", {})
        .get("case_id")
    )


def get_case_info(case_data):
    return case_data.get(
        "case",
        {}
    )


def get_lot(case_data):
    return case_data.get("lot")


def get_documents(
    case_data,
    document_type=None
):
    documents = case_data.get(
        "documents",
        []
    )

    if document_type is None:
        return documents

    return [
        document
        for document in documents
        if document.get(
            "document_type"
        ) == document_type
    ]


def get_latest_document(
    case_data,
    document_type
):
    documents = get_documents(
        case_data,
        document_type
    )

    if not documents:
        return None

    # case_repository에서 ID 순으로 들어오므로
    # 뒤쪽 문서가 보완자료일 가능성이 높음
    for document in reversed(
        documents
    ):
        if document.get(
            "structured_data"
        ) is not None:
            return document

    return documents[-1]


def get_characteristic(
    structured_data
):
    if not structured_data:
        return {}

    characteristics = (
        structured_data.get(
            "characteristics",
            []
        )
    )

    if not characteristics:
        return {}

    return characteristics[0]


def get_drawing_pair(case_data):
    drawings = [
        document
        for document in get_documents(
            case_data,
            "DRAWING"
        )
        if document.get(
            "structured_data"
        )
    ]

    if len(drawings) < 2:
        return None, None

    case_info = get_case_info(
        case_data
    )

    required_revision = (
        case_info.get(
            "drawing_revision"
        )
    )

    new_drawing = None

    if required_revision is not None:
        for document in reversed(
            drawings
        ):
            revision = (
                document[
                    "structured_data"
                ].get("revision")
            )

            if revision == required_revision:
                new_drawing = document
                break

    # drawing_revision으로 못 찾으면
    # Revision 문자열 기준 마지막 도면 사용
    if new_drawing is None:
        drawings = sorted(
            drawings,
            key=lambda item: str(
                item[
                    "structured_data"
                ].get(
                    "revision",
                    ""
                )
            )
        )

        new_drawing = drawings[-1]

    old_candidates = [
        document
        for document in drawings
        if document is not new_drawing
    ]

    if not old_candidates:
        return None, new_drawing

    old_drawing = old_candidates[-1]

    return old_drawing, new_drawing


def extract_requirements(case_data):
    old_drawing, new_drawing = (
        get_drawing_pair(
            case_data
        )
    )

    if new_drawing is None:
        return {}, []

    new_data = (
        new_drawing.get(
            "structured_data"
        )
        or {}
    )

    characteristic = (
        get_characteristic(
            new_data
        )
    )

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
            characteristic.get(
                "nominal_mm"
            ),

        "tolerance_mm":
            characteristic.get(
                "tolerance_mm"
            )
    }

    evidence = [
        {
            "role":
                "REQUIREMENT_DRAWING",

            "file_name":
                new_drawing.get(
                    "file_name"
                ),

            "document_type":
                "DRAWING",

            "revision":
                requirements[
                    "revision"
                ]
        }
    ]

    return requirements, evidence


def extract_actual_values(case_data):
    lot = get_lot(
        case_data
    ) or {}

    inspection_document = (
        get_latest_document(
            case_data,
            "INSPECTION_REPORT"
        )
    )

    material_document = (
        get_latest_document(
            case_data,
            "MATERIAL_CERTIFICATE"
        )
    )

    heat_document = (
        get_latest_document(
            case_data,
            "HEAT_TREATMENT_CERTIFICATE"
        )
    )

    inspection = (
        inspection_document.get(
            "structured_data"
        )
        if inspection_document
        else None
    )

    material = (
        material_document.get(
            "structured_data"
        )
        if material_document
        else None
    )

    heat = (
        heat_document.get(
            "structured_data"
        )
        if heat_document
        else None
    )

    actual = {
        "lot_no":
            lot.get("lot_no"),

        "lot_revision":
            lot.get("revision"),

        "inspection_present":
            inspection_document
            is not None,

        "inspection_lot_no":
            (
                inspection.get(
                    "lot_no"
                )
                if inspection
                else None
            ),

        "inspection_revision":
            (
                inspection.get(
                    "revision"
                )
                if inspection
                else None
            ),

        "measured_mm":
            (
                inspection.get(
                    "measured_mm"
                )
                if inspection
                else None
            ),

        "material":
            (
                material.get(
                    "material"
                )
                if material
                else None
            ),

        "material_heat_no":
            (
                material.get(
                    "heat_no"
                )
                if material
                else None
            ),

        "heat_treatment":
            (
                heat.get(
                    "heat_treatment"
                )
                if heat
                else None
            ),

        "heat_heat_no":
            (
                heat.get(
                    "heat_no"
                )
                if heat
                else None
            )
    }

    evidence = []

    for document in [
        inspection_document,
        material_document,
        heat_document
    ]:
        if document is None:
            continue

        evidence.append({
            "file_name":
                document.get(
                    "file_name"
                ),

            "document_type":
                document.get(
                    "document_type"
                ),

            "document_stage":
                document.get(
                    "document_stage"
                )
        })

    return actual, evidence


def get_received_document_types(
    case_data
):
    return {
        document.get(
            "document_type"
        )
        for document
        in get_documents(
            case_data
        )
    }


def normalize_required_documents(
    required_documents
):
    result = []

    for item in (
        required_documents
        or []
    ):

        if isinstance(item, dict):
            document_type = (
                item.get(
                    "required_document_type"
                )
                or item.get(
                    "required_document"
                )
            )
        else:
            document_type = item

        if (
            document_type
            and document_type
            not in result
        ):
            result.append(
                document_type
            )

    return result


def parse_date(value):
    if not value:
        return None

    try:
        return datetime.strptime(
            value,
            "%Y-%m-%d"
        ).date()

    except ValueError:
        return None