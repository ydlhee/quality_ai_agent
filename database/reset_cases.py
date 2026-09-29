import sqlite3
from pathlib import Path

from import_cases import IMPORT_CASE_IDS, import_cases


DB_PATH = Path(__file__).resolve().parent / "sample_lots.db"


def reset_cases():
    """
    테스트용 Case만 최초 수신 상태로 초기화한다.

    초기화 대상:
    - CASE-001
    - CASE-002
    - CASE-003

    Gmail을 통해 생성된 실제 Case 등
    IMPORT_CASE_IDS에 포함되지 않은 Case는 보존한다.
    """

    if not DB_PATH.exists():
        raise FileNotFoundError(f"DB가 없습니다: {DB_PATH}")

    placeholders = ",".join("?" for _ in IMPORT_CASE_IDS)

    conn = sqlite3.connect(DB_PATH)

    try:
        conn.execute("BEGIN")

        # 테스트 Case에 연결된 문서만 삭제
        conn.execute(
            f"""
            DELETE FROM case_documents
            WHERE case_id IN ({placeholders})
            """,
            IMPORT_CASE_IDS,
        )

        # 테스트 Case 본체만 삭제
        conn.execute(
            f"""
            DELETE FROM cases
            WHERE case_id IN ({placeholders})
            """,
            IMPORT_CASE_IDS,
        )

        conn.commit()

        print(
            "테스트 Case 초기화 완료: "
            + ", ".join(IMPORT_CASE_IDS)
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    # CASE-001~003을 최초 상태로 다시 등록
    import_cases()


if __name__ == "__main__":
    reset_cases()