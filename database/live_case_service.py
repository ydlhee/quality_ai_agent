import json

import re

import sqlite3

from pathlib import Path



from database.mail_case_repository import (

    get_case_id_by_thread,

    save_thread_case_mapping,

)





DB_PATH = Path(__file__).resolve().parent / "sample_lots.db"





# ============================================================

# 공통 함수

# ============================================================



def _connect():

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    return conn





def _successful_documents(mail_result):

    """

    Parser가 SUCCESS인 문서만 반환한다.

    신규 Case 생성 시 WARNING / ERROR / UNSUPPORTED 문서는

    자동 등록하지 않는다.

    """

    return [

        document

        for document in mail_result.get("parsed_documents", [])

        if document.get("parse_status") == "SUCCESS"

        and document.get("structured_data")

    ]





def _documents_by_type(documents):

    grouped = {}



    for document in documents:

        document_type = document.get("document_type")



        grouped.setdefault(

            document_type,

            [],

        ).append(document)



    return grouped





def _unique_non_empty(values):

    return {

        value

        for value in values

        if value not in (None, "")

    }





# ============================================================

# 신규 Case 번호 생성

# ============================================================



def _generate_next_case_id(conn):

    """

    기존 CASE-001, CASE-002 ... 중 가장 큰 숫자를 찾아

    다음 Case ID를 만든다.



    예:

        CASE-001

        CASE-002

        CASE-003



    -> CASE-004

    """



    rows = conn.execute(

        """

        SELECT case_id

        FROM cases

        """

    ).fetchall()



    max_number = 0



    for row in rows:

        case_id = row["case_id"]



        match = re.fullmatch(

            r"CASE-(\d+)",

            case_id or "",

            flags=re.IGNORECASE,

        )



        if not match:

            continue



        number = int(match.group(1))

        max_number = max(max_number, number)



    return f"CASE-{max_number + 1:03d}"





# ============================================================

# 메일 문서 일관성 검증

# ============================================================



def validate_new_case_mail(mail_result):
    """
    신규 Case 생성 전에 메일과 첨부문서의 식별정보 일관성을 검증한다.

    신규 Case 생성에 필요한 최소 문서:
    - 변경 전 Drawing
    - 변경 후 Drawing
    - Material Certificate
    - Heat Treatment Certificate

    Inspection Report는 Case 생성의 필수조건으로 두지 않는다.
    검사성적서가 누락된 경우에도 Case를 생성하고,
    이후 품질검증 Tool이 REQUIRED_DOCUMENT_MISSING으로 HOLD 판정한다.

    Inspection Report가 함께 수신된 경우에는
    Part / PO / Lot / Revision 일관성 검증에 포함한다.
    """
    errors = []

    if mail_result.get("mail_type") != "NEW":
        errors.append("신규 Case 후보 메일이 아닙니다.")

    thread_id = mail_result.get("thread_id")
    if not thread_id:
        errors.append("Gmail Thread ID가 없습니다.")

    documents = _successful_documents(mail_result)
    grouped = _documents_by_type(documents)

    drawings = grouped.get("DRAWING", [])
    inspections = grouped.get("INSPECTION_REPORT", [])
    material_certificates = grouped.get("MATERIAL_CERTIFICATE", [])
    heat_certificates = grouped.get("HEAT_TREATMENT_CERTIFICATE", [])

    # Case 생성에 필요한 최소 문서 확인
    if len(drawings) < 2:
        errors.append("변경 전·후 도면 2개가 필요합니다.")

    # 검사성적서는 여기서 필수조건으로 검사하지 않는다.
    # 누락 여부는 품질검증 Tool에서 판단하여 HOLD로 처리한다.

    if not material_certificates:
        errors.append("소재성적서가 없습니다.")

    if not heat_certificates:
        errors.append("열처리성적서가 없습니다.")

    if errors:
        return {
            "valid": False,
            "errors": errors,
            "case_data": None,
        }

    # Drawing 정렬
    drawings = sorted(
        drawings,
        key=lambda document: (
            document["structured_data"].get("effective_from", "")
        ),
    )

    old_drawing = drawings[0]
    new_drawing = drawings[-1]

    old_data = old_drawing["structured_data"]
    new_data = new_drawing["structured_data"]

    # 검사성적서는 선택 문서
    inspection_data = (
        inspections[0]["structured_data"]
        if inspections
        else {}
    )

    material_data = material_certificates[0]["structured_data"]
    heat_data = heat_certificates[0]["structured_data"]

    # Part 일치 확인
    part_numbers = _unique_non_empty([
        old_data.get("part_no"),
        new_data.get("part_no"),
        inspection_data.get("part_no"),
        material_data.get("part_no"),
        heat_data.get("part_no"),
    ])

    if len(part_numbers) != 1:
        errors.append("첨부문서 간 Part No가 일치하지 않습니다.")

    # Drawing No 일치 확인
    drawing_numbers = _unique_non_empty([
        old_data.get("drawing_no"),
        new_data.get("drawing_no"),
    ])

    if len(drawing_numbers) != 1:
        errors.append("변경 전·후 Drawing No가 일치하지 않습니다.")

    # PO 일치 확인
    po_numbers = _unique_non_empty([
        inspection_data.get("po_no"),
        material_data.get("po_no"),
        heat_data.get("po_no"),
    ])

    if len(po_numbers) != 1:
        errors.append("수신된 품질문서 간 PO No가 일치하지 않습니다.")

    # Lot 일치 확인
    lot_numbers = _unique_non_empty([
        inspection_data.get("lot_no"),
        material_data.get("lot_no"),
        heat_data.get("lot_no"),
    ])

    if len(lot_numbers) != 1:
        errors.append("수신된 품질문서 간 Lot No가 일치하지 않습니다.")

    # Supplier 일치 확인
    supplier_ids = _unique_non_empty([
        material_data.get("supplier_id"),
        heat_data.get("supplier_id"),
    ])

    if len(supplier_ids) != 1:
        errors.append(
            "소재·열처리 문서의 Supplier ID가 일치하지 않습니다."
        )

    # 변경 후 Revision 일치 확인
    # 검사성적서가 실제로 있을 때만 검사한다.
    new_revision = new_data.get("revision")
    inspection_revision = inspection_data.get("revision")

    if (
        new_revision
        and inspection_revision
        and new_revision != inspection_revision
    ):
        errors.append(
            "변경 후 도면 Revision과 검사성적서 Revision이 "
            "일치하지 않습니다."
        )

    if errors:
        return {
            "valid": False,
            "errors": errors,
            "case_data": None,
        }

    part_no = next(iter(part_numbers))
    po_no = next(iter(po_numbers))
    lot_no = next(iter(lot_numbers))
    supplier_id = next(iter(supplier_ids))

    return {
        "valid": True,
        "errors": [],
        "case_data": {
            "part_no": part_no,
            "po_no": po_no,
            "lot_no": lot_no,
            "supplier_id": supplier_id,
            "drawing_no": next(iter(drawing_numbers)),
            "old_revision": old_data.get("revision"),
            "new_revision": new_revision,
            "effective_from": new_data.get("effective_from"),
        },
    }


# ============================================================

# Master DB 검증

# ============================================================



def _validate_master_data(

    conn,

    case_data,

):

    """

    메일에서 추출한 식별정보가 기존 Master DB와

    실제로 연결되는지 확인한다.

    """



    errors = []



    part_no = case_data["part_no"]

    po_no = case_data["po_no"]

    lot_no = case_data["lot_no"]

    supplier_id = case_data[

        "supplier_id"

    ]



    part_row = conn.execute(

        """

        SELECT *

        FROM parts

        WHERE part_no = ?

        """,

        (part_no,),

    ).fetchone()



    if part_row is None:

        errors.append(

            f"DB에 Part {part_no}가 없습니다."

        )



    supplier_row = conn.execute(

        """

        SELECT *

        FROM suppliers

        WHERE supplier_id = ?

        """,

        (supplier_id,),

    ).fetchone()



    if supplier_row is None:

        errors.append(

            f"DB에 Supplier {supplier_id}가 없습니다."

        )



    po_row = conn.execute(

        """

        SELECT *

        FROM purchase_orders

        WHERE po_no = ?

        """,

        (po_no,),

    ).fetchone()



    if po_row is None:

        errors.append(

            f"DB에 PO {po_no}가 없습니다."

        )



    lot_row = conn.execute(

        """

        SELECT *

        FROM lot_samples

        WHERE lot_no = ?

        """,

        (lot_no,),

    ).fetchone()



    if lot_row is None:

        errors.append(

            f"DB에 Lot {lot_no}가 없습니다."

        )



    if errors:

        return {

            "valid": False,

            "errors": errors,

            "supplier_name": None,

        }



    # --------------------------------------------------------

    # PO 관계 검증

    # --------------------------------------------------------



    po_data = dict(po_row)



    if (

        po_data.get("part_no")

        and po_data["part_no"] != part_no

    ):

        errors.append(

            "PO에 연결된 Part와 메일의 Part가 일치하지 않습니다."

        )



    if (

        po_data.get("supplier_id")

        and po_data["supplier_id"]

        != supplier_id

    ):

        errors.append(

            "PO에 연결된 Supplier와 메일의 Supplier가 일치하지 않습니다."

        )



    # --------------------------------------------------------

    # Lot 관계 검증

    # --------------------------------------------------------



    lot_data = dict(lot_row)



    if (

        lot_data.get("part_no")

        and lot_data["part_no"] != part_no

    ):

        errors.append(

            "Lot에 연결된 Part와 메일의 Part가 일치하지 않습니다."

        )



    if (

        lot_data.get("po_no")

        and lot_data["po_no"] != po_no

    ):

        errors.append(

            "Lot에 연결된 PO와 메일의 PO가 일치하지 않습니다."

        )



    supplier_name = dict(

        supplier_row

    ).get(

        "supplier_name",

        supplier_id,

    )



    return {

        "valid": not errors,

        "errors": errors,

        "supplier_name": supplier_name,

    }





# ============================================================

# Parser 결과 DB 저장

# ============================================================



def _save_inspection_document(

    conn,

    document,

):

    data = document["structured_data"]



    conn.execute(

        """

        INSERT OR REPLACE INTO inspection_documents (

            source_file,

            document_id,

            lot_no,

            part_no,

            extracted_json

        )

        VALUES (?, ?, ?, ?, ?)

        """,

        (

            document["file_name"],

            data.get("document_id"),

            data.get("lot_no"),

            data.get("part_no"),

            json.dumps(

                data,

                ensure_ascii=False,

            ),

        ),

    )





def _save_quality_certificate(

    conn,

    document,

):

    data = document["structured_data"]



    conn.execute(

        """

        INSERT OR REPLACE INTO quality_certificates (

            certificate_id,

            certificate_type,

            part_no,

            po_no,

            lot_no,

            supplier_id,

            material,

            heat_treatment,

            heat_no,

            source_file,

            extracted_json

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        """,

        (

            data.get("certificate_id"),

            data.get("certificate_type"),

            data.get("part_no"),

            data.get("po_no"),

            data.get("lot_no"),

            data.get("supplier_id"),

            data.get("material"),

            data.get("heat_treatment"),

            data.get("heat_no"),

            document["file_name"],

            json.dumps(

                data,

                ensure_ascii=False,

            ),

        ),

    )





# ============================================================

# 신규 Live Case 생성

# ============================================================



def create_live_case(mail_result):

    """

    실제 Gmail 신규 메일을 기존 Case 구조에 등록한다.



    처리 순서:

    1. 이미 연결된 Gmail Thread인지 확인

    2. Parser 결과 일관성 검증

    3. Master DB 관계 검증

    4. 신규 Case ID 생성

    5. cases 등록

    6. case_documents 등록

    7. Parser 구조화 데이터 등록

    8. Gmail Thread ↔ Case 연결

    """



    thread_id = mail_result.get(

        "thread_id"

    )



    if not thread_id:

        return {

            "success": False,

            "case_id": None,

            "errors": [

                "Gmail Thread ID가 없습니다."

            ],

        }



    # --------------------------------------------------------

    # 중복 생성 방지

    # --------------------------------------------------------



    existing_case_id = (

        get_case_id_by_thread(

            thread_id

        )

    )



    if existing_case_id:

        return {

            "success": True,

            "case_id": existing_case_id,

            "already_exists": True,

            "errors": [],

        }



    # --------------------------------------------------------

    # 문서 일관성 검증

    # --------------------------------------------------------



    validation = validate_new_case_mail(

        mail_result

    )



    if not validation["valid"]:

        return {

            "success": False,

            "case_id": None,

            "already_exists": False,

            "errors": validation["errors"],

        }



    case_data = validation[

        "case_data"

    ]



    conn = _connect()



    try:

        # ----------------------------------------------------

        # Master DB 검증

        # ----------------------------------------------------



        master_validation = (

            _validate_master_data(

                conn,

                case_data,

            )

        )



        if not master_validation["valid"]:

            return {

                "success": False,

                "case_id": None,

                "already_exists": False,

                "errors": master_validation[

                    "errors"

                ],

            }



        supplier_name = master_validation[

            "supplier_name"

        ]



        # ----------------------------------------------------

        # Case ID 생성

        # ----------------------------------------------------



        case_id = _generate_next_case_id(

            conn

        )



        # ----------------------------------------------------

        # Case 등록

        # ----------------------------------------------------



        conn.execute(

            """

            INSERT INTO cases (

                case_id,

                part_no,

                po_no,

                lot_no,

                supplier_id,

                supplier_name,

                drawing_revision,

                case_status

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?)

            """,

            (

                case_id,

                case_data["part_no"],

                case_data["po_no"],

                case_data["lot_no"],

                case_data["supplier_id"],

                supplier_name,

                case_data["new_revision"],

                "OPEN",

            ),

        )



        # ----------------------------------------------------

        # 문서 등록

        # ----------------------------------------------------



        documents = _successful_documents(

            mail_result

        )



        source_email = (

            mail_result.get("message_id")

            or mail_result.get("from")

            or ""

        )



        for document in documents:



            conn.execute(

                """

                INSERT INTO case_documents (

                    case_id,

                    file_name,

                    document_type,

                    document_stage,

                    source_email

                )

                VALUES (?, ?, ?, ?, ?)

                """,

                (

                    case_id,

                    document["file_name"],

                    document["document_type"],

                    "INITIAL",

                    source_email,

                ),

            )



            if (

                document["document_type"]

                == "INSPECTION_REPORT"

            ):

                _save_inspection_document(

                    conn,

                    document,

                )



            elif document[

                "document_type"

            ] in {

                "MATERIAL_CERTIFICATE",

                "HEAT_TREATMENT_CERTIFICATE",

            }:

                _save_quality_certificate(

                    conn,

                    document,

                )



        conn.commit()



        # ----------------------------------------------------

        # Gmail Thread ↔ Case 연결

        # ----------------------------------------------------



        save_thread_case_mapping(

            thread_id=thread_id,

            case_id=case_id,

            initial_message_id=mail_result.get(

                "message_id"

            ),

            sender=mail_result.get(

                "from"

            ),

            subject=mail_result.get(

                "subject"

            ),

        )



        return {

            "success": True,

            "case_id": case_id,

            "already_exists": False,

            "errors": [],

            "case_data": case_data,

        }



    except Exception as error:

        conn.rollback()



        return {

            "success": False,

            "case_id": None,

            "already_exists": False,

            "errors": [

                str(error)

            ],

        }



    finally:

        conn.close()