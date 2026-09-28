import json
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
TEST_CASE_DIR = BASE_DIR / "data" / "test_cases"
DB_PATH = Path(__file__).resolve().parent / "sample_lots.db"


def get_document_type(file_name):
    if file_name.startswith("DWG-"):
        return "DRAWING"

    if file_name.startswith("INS-"):
        return "INSPECTION_REPORT"

    return "OTHER"


def import_cases():
    conn = sqlite3.connect(DB_PATH)

    try:
        # Case 기본정보
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                part_no TEXT NOT NULL,
                po_no TEXT NOT NULL,
                lot_no TEXT NOT NULL,
                supplier_id TEXT NOT NULL,
                supplier_name TEXT NOT NULL,
                drawing_revision TEXT NOT NULL,
                case_status TEXT NOT NULL
            )
            """
        )

        # Case에 연결된 문서
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS case_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                document_type TEXT NOT NULL,
                document_stage TEXT NOT NULL,
                source_email TEXT NOT NULL,
                UNIQUE(case_id, file_name, document_stage)
            )
            """
        )

        case_count = 0
        document_count = 0

        for case_dir in sorted(TEST_CASE_DIR.iterdir()):
            if not case_dir.is_dir():
                continue

            case_json_path = case_dir / "case.json"
            email_json_path = case_dir / "initial_email.json"

            case_data = json.loads(
                case_json_path.read_text(
                    encoding="utf-8"
                )
            )

            email_data = json.loads(
                email_json_path.read_text(
                    encoding="utf-8"
                )
            )

            conn.execute(
                """
                INSERT OR REPLACE INTO cases
                (
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
                    case_data["case_id"],
                    case_data["part_no"],
                    case_data["po_no"],
                    case_data["lot_no"],
                    case_data["supplier_id"],
                    case_data["supplier_name"],
                    case_data["drawing_revision"],
                    case_data["case_status"],
                ),
            )

            case_count += 1

            # 최초 메일의 첨부파일만 등록
            # supplemental 자료는 아직 등록하지 않음
            for file_name in email_data["attachment_files"]:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO case_documents
                    (
                        case_id,
                        file_name,
                        document_type,
                        document_stage,
                        source_email
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        case_data["case_id"],
                        file_name,
                        get_document_type(file_name),
                        "INITIAL",
                        "initial_email.json",
                    ),
                )

                document_count += 1

        conn.commit()

        print(f"Case {case_count}개 저장 완료")
        print(
            f"최초 첨부문서 {document_count}개 저장 완료"
        )

        print("\n[Cases]")

        for row in conn.execute(
            """
            SELECT
                case_id,
                part_no,
                lot_no,
                case_status
            FROM cases
            ORDER BY case_id
            """
        ):
            print(
                f"{row[0]} | "
                f"{row[1]} | "
                f"{row[2]} | "
                f"{row[3]}"
            )

        print("\n[Case Documents]")

        for row in conn.execute(
            """
            SELECT
                case_id,
                file_name,
                document_stage
            FROM case_documents
            ORDER BY case_id, file_name
            """
        ):
            print(
                f"{row[0]} | "
                f"{row[1]} | "
                f"{row[2]}"
            )

    finally:
        conn.close()


if __name__ == "__main__":
    import_cases()