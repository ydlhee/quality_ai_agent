import json
import sqlite3
from pathlib import Path


# ============================================================
# 기본 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(__file__).resolve().parent / "sample_lots.db"

# 기존 테스트 Case 파일 경로
TEST_CASE_DIR = BASE_DIR / "data" / "test_cases"

# 실제 Gmail에서 다운로드한 첨부파일 경로
MAIL_ATTACHMENT_DIR = BASE_DIR / "data" / "mail_attachments"


# ============================================================
# JSON 파일 로드
# ============================================================

def load_json(path):
    if not path.exists():
        return None

    return json.loads(
        path.read_text(encoding="utf-8")
    )


# ============================================================
# 문서 실제 경로 찾기
# ============================================================

def get_document_path(
    case_id,
    file_name,
    stage,
    source_email=None,
):
    """
    Case 문서의 실제 파일 경로를 반환한다.

    1. Gmail을 통해 생성된 Live Case의 경우
       data/mail_attachments/<message_id>/<file_name>

    2. Gmail 경로에서 파일을 찾을 수 없는 경우
       기존 테스트 Case 경로 사용
       data/test_cases/<case_id>/...
    """

    # --------------------------------------------------------
    # 1. 실제 Gmail 첨부파일 경로 확인
    # --------------------------------------------------------

    if source_email:
        mail_path = (
            MAIL_ATTACHMENT_DIR
            / source_email
            / file_name
        )

        if mail_path.exists():
            return str(mail_path)

    # --------------------------------------------------------
    # 2. 기존 테스트 Case 경로
    # --------------------------------------------------------

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


# ============================================================
# Case 조회
# ============================================================

def get_case(case_id):
    """
    Case ID 하나를 기준으로 다음 정보를 조회한다.

    - Case 기본정보
    - 메일 정보
    - Lot 정보
    - 현재 등록된 문서
    - 문서 구조화 데이터
    - 실제 문서 파일 경로
    """

    if not DB_PATH.exists():
        raise FileNotFoundError(
            "DB가 없습니다. import_cases.py를 먼저 실행하세요."
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:

        # ====================================================
        # 1. Case 기본정보
        # ====================================================

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

        # ====================================================
        # 2. Lot 정보
        # ====================================================

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

        # ====================================================
        # 3. 현재 Case에 등록된 문서 조회
        # ====================================================

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

        # ====================================================
        # 4. 각 문서의 구조화 데이터 조회
        # ====================================================

        for row in document_rows:

            document = dict(row)

            # ------------------------------------------------
            # 실제 PDF 파일 경로 결정
            #
            # Gmail Case:
            # data/mail_attachments/<message_id>/<file>
            #
            # 기존 테스트 Case:
            # data/test_cases/<case_id>/...
            # ------------------------------------------------

            document["file_path"] = get_document_path(
                case_id,
                document["file_name"],
                document["document_stage"],
                document["source_email"],
            )

            structured_data = None

            # =================================================
            # 도면 구조화 데이터
            # =================================================

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

            # =================================================
            # 검사성적서 구조화 데이터
            # =================================================

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

            # =================================================
            # 소재성적서 / 열처리성적서 구조화 데이터
            # =================================================

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

        # ====================================================
        # 5. 기존 테스트 Case 메일 데이터
        # ====================================================

        case_dir = TEST_CASE_DIR / case_id

        initial_email = load_json(
            case_dir / "initial_email.json"
        )

        # ====================================================
        # 6. 보완자료 존재 여부 확인
        # ====================================================

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

        # ====================================================
        # 7. 최종 Case 데이터 반환
        # ====================================================

        return {
            "case": case_data,
            "initial_email": initial_email,
            "supplemental_email": supplemental_email,
            "lot": lot_data,
            "documents": documents,
        }

    finally:
        conn.close()


# ============================================================
# Case 상태 저장
# ============================================================

def update_case_status(case_id, case_status):
    """
    Agent가 결정한 Case 상태를 cases 테이블에 저장한다.

    주요 상태:
    - OPEN
    - REVALIDATING
    - WAITING_FOR_CORRECTION
    - WAITING_FOR_CORRECTIVE_ACTION
    - WAITING
    - COMPLETED
    """

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DB가 없습니다: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)

    try:
        cursor = conn.execute(
            """
            UPDATE cases
            SET case_status = ?
            WHERE case_id = ?
            """,
            (case_status, case_id),
        )

        if cursor.rowcount == 0:
            raise ValueError(
                f"Case를 찾을 수 없습니다: {case_id}"
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# ============================================================
# 단독 실행 테스트
# ============================================================

if __name__ == "__main__":

    result = get_case("CASE-002")

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )