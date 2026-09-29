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


def import_supplemental(case_id):
    """
    기존 Case에 협력사의 보완자료를 추가한다.
    신규 Case는 생성하지 않는다.
    """

    case_dir = TEST_CASE_DIR / case_id

    supplemental_email_path = (
        case_dir / "supplemental_email.json"
    )

    if not supplemental_email_path.exists():
        raise FileNotFoundError(
            f"{case_id}의 supplemental_email.json이 없습니다."
        )

    email_data = json.loads(
        supplemental_email_path.read_text(
            encoding="utf-8"
        )
    )

    conn = sqlite3.connect(DB_PATH)

    try:
        # 기존 Case가 실제로 있는지 확인
        case_row = conn.execute(
            """
            SELECT case_id
            FROM cases
            WHERE case_id = ?
            """,
            (case_id,),
        ).fetchone()

        if case_row is None:
            raise ValueError(
                f"기존 Case를 찾을 수 없습니다: {case_id}"
            )

        added_count = 0

        for file_name in email_data["attachment_files"]:
            conn.execute(
                """
                INSERT OR IGNORE INTO case_documents
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
                    case_id,
                    file_name,
                    get_document_type(file_name),
                    "SUPPLEMENTAL",
                    "supplemental_email.json",
                ),
            )

            added_count += 1

        conn.commit()

        print(
            f"{case_id}에 보완자료 "
            f"{added_count}개 등록 완료"
        )

        print("\n[현재 Case 문서]")

        rows = conn.execute(
            """
            SELECT
                file_name,
                document_type,
                document_stage
            FROM case_documents
            WHERE case_id = ?
            ORDER BY id
            """,
            (case_id,),
        ).fetchall()

        for row in rows:
            print(
                f"{row[0]} | "
                f"{row[1]} | "
                f"{row[2]}"
            )

    finally:
        conn.close()


if __name__ == "__main__":
    import_supplemental("CASE-002")