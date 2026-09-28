import json
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(__file__).resolve().parent / "sample_lots.db"
TEST_CASE_DIR = BASE_DIR / "data" / "test_cases"


def load_json(path):
    if not path.exists():
        return None

    return json.loads(
        path.read_text(encoding="utf-8")
    )


def get_document_path(case_id, file_name, stage):
    case_dir = TEST_CASE_DIR / case_id

    if stage == "INITIAL":
        return str(
            case_dir
            / "initial_attachments"
            / file_name
        )

    if stage == "SUPPLEMENTAL":
        return str(
            case_dir
            / "supplemental_attachments"
            / file_name
        )

    return None


def get_case(case_id):
    """
    Case ID 하나를 기준으로
    Case 정보 + 메일 + Lot 정보 + 현재 등록 문서
    + 문서의 구조화 데이터를 조회한다.
    """

    if not DB_PATH.exists():
        raise FileNotFoundError(
            "DB가 없습니다. import_cases.py를 먼저 실행하세요."
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        # 1. Case 기본정보
        case_row = conn.execute(
            """
            SELECT *
            FROM cases
            WHERE case_id = ?
            """,
            (case_id,),
        ).fetchone()

        if case_row is None:
            return None

        case_data = dict(case_row)

        # 2. Lot 정보
        lot_row = conn.execute(
            """
            SELECT *
            FROM lot_samples
            WHERE lot_no = ?
            """,
            (case_data["lot_no"],),
        ).fetchone()

        lot_data = (
            dict(lot_row)
            if lot_row is not None
            else None
        )

        # 3. 현재 Case에 등록된 문서 조회
        document_rows = conn.execute(
            """
            SELECT
                file_name,
                document_type,
                document_stage,
                source_email
            FROM case_documents
            WHERE case_id = ?
            ORDER BY id
            """,
            (case_id,),
        ).fetchall()

        documents = []

        for row in document_rows:
            document = dict(row)

            document["file_path"] = (
                get_document_path(
                    case_id,
                    document["file_name"],
                    document["document_stage"],
                )
            )

            structured_data = None

            # 도면 구조화 데이터
            if document["document_type"] == "DRAWING":
                drawing_rows = conn.execute(
                    """
                    SELECT drawing_json
                    FROM drawings
                    WHERE part_no = ?
                    """,
                    (case_data["part_no"],),
                ).fetchall()

                for drawing_row in drawing_rows:
                    drawing_data = json.loads(
                        drawing_row["drawing_json"]
                    )

                    if (
                        drawing_data.get("source_file")
                        == document["file_name"]
                    ):
                        structured_data = drawing_data
                        break

            # 검사성적서 구조화 데이터
            elif (
                document["document_type"]
                == "INSPECTION_REPORT"
            ):
                inspection_row = conn.execute(
                    """
                    SELECT extracted_json
                    FROM inspection_documents
                    WHERE source_file = ?
                      AND lot_no = ?
                    """,
                    (
                        document["file_name"],
                        case_data["lot_no"],
                    ),
                ).fetchone()

                if inspection_row is not None:
                    structured_data = json.loads(
                        inspection_row["extracted_json"]
                    )

            # 소재성적서 / 열처리성적서 구조화 데이터
            elif document["document_type"] in (
                "MATERIAL_CERTIFICATE",
                "HEAT_TREATMENT_CERTIFICATE",
            ):
                certificate_row = conn.execute(
                    """
                    SELECT extracted_json
                    FROM quality_certificates
                    WHERE source_file = ?
                      AND lot_no = ?
                    """,
                    (
                        document["file_name"],
                        case_data["lot_no"],
                    ),
                ).fetchone()

                if certificate_row is not None:
                    structured_data = json.loads(
                        certificate_row["extracted_json"]
                    )

            document["structured_data"] = structured_data

            documents.append(document)

        # 4. 메일 데이터
        case_dir = TEST_CASE_DIR / case_id

        initial_email = load_json(
            case_dir / "initial_email.json"
        )

        has_supplemental = any(
            document["document_stage"] == "SUPPLEMENTAL"
            for document in documents
        )

        supplemental_email = (
            load_json(
                case_dir / "supplemental_email.json"
            )
            if has_supplemental
            else None
        )

        # 5. 최종 Case 데이터 반환
        return {
            "case": case_data,
            "initial_email": initial_email,
            "supplemental_email": supplemental_email,
            "lot": lot_data,
            "documents": documents,
        }

    finally:
        conn.close()


if __name__ == "__main__":
    result = get_case("CASE-002")

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )