import json
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
TEST_CASE_DIR = BASE_DIR / "data" / "test_cases"
DB_PATH = Path(__file__).resolve().parent / "sample_lots.db"

# 이 importer가 담당하는 기존 메일 테스트 Case
IMPORT_CASE_IDS = ("CASE-001", "CASE-002", "CASE-003")

IDENTITY_FIELDS = (
    "part_no",
    "po_no",
    "lot_no",
    "supplier_id",
    "supplier_name",
    "drawing_revision",
)

REQUIRED_FIELDS = (
    "case_id",
    *IDENTITY_FIELDS,
    "case_status",
)


def get_document_type(file_name):
    if file_name.startswith("DWG-"):
        return "DRAWING"
    if file_name.startswith("INS-"):
        return "INSPECTION_REPORT"
    if file_name.startswith("MAT-"):
        return "MATERIAL_CERTIFICATE"
    if file_name.startswith("HT-"):
        return "HEAT_TREATMENT_CERTIFICATE"
    return "OTHER"


def read_json(path):
    if not path.is_file():
        raise FileNotFoundError(
            f"가져올 대상 Case의 필수 파일이 없습니다: {path}"
        )

    data = json.loads(path.read_text(encoding="utf-8-sig"))

    if not isinstance(data, dict):
        raise ValueError(f"JSON은 객체 형식이어야 합니다: {path}")

    return data


def load_cases():
    """DB에 쓰기 전에 대상 파일을 모두 확인한다."""
    if not TEST_CASE_DIR.is_dir():
        raise FileNotFoundError(
            f"Case 폴더가 없습니다: {TEST_CASE_DIR}"
        )

    for folder in sorted(TEST_CASE_DIR.iterdir()):
        if folder.is_dir() and folder.name not in IMPORT_CASE_IDS:
            print(f"[대상 제외] {folder.name}")

    records = []

    for case_id in IMPORT_CASE_IDS:
        case_dir = TEST_CASE_DIR / case_id
        case_data = read_json(case_dir / "case.json")
        email_data = read_json(case_dir / "initial_email.json")

        for field in REQUIRED_FIELDS:
            value = case_data.get(field)

            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{case_id}: {field} 항목이 없거나 "
                    "비어 있는 문자열입니다."
                )

        if case_data["case_id"] != case_id:
            raise ValueError(
                f"폴더명 {case_id}와 JSON의 case_id "
                f"{case_data['case_id']}가 다릅니다."
            )

        attachments = email_data.get("attachment_files")

        if not isinstance(attachments, list):
            raise ValueError(
                f"{case_id}: attachment_files는 목록이어야 합니다."
            )

        if any(
            not isinstance(name, str) or not name.strip()
            for name in attachments
        ):
            raise ValueError(
                f"{case_id}: 첨부파일 이름이 잘못되었습니다."
            )

        if len(attachments) != len(set(attachments)):
            raise ValueError(
                f"{case_id}: attachment_files에 중복이 있습니다."
            )

        records.append((case_data, attachments))

    return records


def import_cases():
    records = load_cases()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    new_cases = 0
    existing_cases = 0
    new_documents = 0

    try:
        # 오류가 발생하면 이번 실행의 변경사항을 모두 취소한다.
        conn.execute("BEGIN")

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

        for case_data, attachments in records:
            case_id = case_data["case_id"]

            existing = conn.execute(
                "SELECT * FROM cases WHERE case_id = ?",
                (case_id,),
            ).fetchone()

            if existing is not None:
                differences = [
                    field
                    for field in IDENTITY_FIELDS
                    if existing[field] != case_data[field]
                ]

                if differences:
                    raise ValueError(
                        f"{case_id}: 같은 ID의 기존 DB 데이터와 "
                        f"기본정보가 다릅니다: {', '.join(differences)}. "
                        "덮어쓰지 않았습니다. 팀원과 Case ID를 "
                        "확인해 주세요."
                    )

                # 기존 상태를 초기 상태로 되돌리지 않는다.
                existing_cases += 1

            else:
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
                    tuple(case_data[field] for field in REQUIRED_FIELDS),
                )
                new_cases += 1

            # 최초 메일 첨부만 추가한다.
            # 기존 문서와 supplemental 자료는 삭제하지 않는다.
            for file_name in attachments:
                document_type = get_document_type(file_name)

                existing_document = conn.execute(
                    """
                    SELECT document_type, source_email
                    FROM case_documents
                    WHERE case_id = ?
                      AND file_name = ?
                      AND document_stage = ?
                    """,
                    (case_id, file_name, "INITIAL"),
                ).fetchone()

                if existing_document is not None:
                    if (
                        existing_document["document_type"] != document_type
                        or existing_document["source_email"]
                        != "initial_email.json"
                    ):
                        raise ValueError(
                            f"{case_id} / {file_name}: "
                            "기존 문서 등록정보와 다릅니다. "
                            "덮어쓰지 않았습니다."
                        )
                    continue

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
                        file_name,
                        document_type,
                        "INITIAL",
                        "initial_email.json",
                    ),
                )
                new_documents += 1

        conn.commit()

        print(f"\n대상 Case {len(records)}개 처리 완료")
        print(f"신규 Case: {new_cases}개")
        print(f"기존 Case 유지: {existing_cases}개")
        print(f"신규 최초 첨부문서: {new_documents}개")

        print("\n[대상 Case 조회]")

        for case_id in IMPORT_CASE_IDS:
            row = conn.execute(
                """
                SELECT case_id, part_no, lot_no, case_status
                FROM cases
                WHERE case_id = ?
                """,
                (case_id,),
            ).fetchone()

            print(
                f"{row['case_id']} | "
                f"{row['part_no']} | "
                f"{row['lot_no']} | "
                f"{row['case_status']}"
            )

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    import_cases()