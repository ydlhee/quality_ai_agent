import sqlite3
from pathlib import Path

from import_cases import import_cases


DB_PATH = Path(__file__).resolve().parent / "sample_lots.db"


def reset_cases():
    """
    Case 데이터를 최초 수신 상태로 초기화한다.

    - 기존 Case 문서 연결 삭제
    - 기존 Case 기본정보 삭제
    - initial_email 기준으로 다시 등록
    - supplemental 자료는 등록하지 않음
    """

    if not DB_PATH.exists():
        raise FileNotFoundError(
            "DB가 없습니다."
        )

    conn = sqlite3.connect(DB_PATH)

    try:
        conn.execute(
            "DELETE FROM case_documents"
        )

        conn.execute(
            "DELETE FROM cases"
        )

        conn.commit()

        print("기존 Case 데이터 초기화 완료")

    finally:
        conn.close()

    # 최초 메일과 최초 첨부문서만 다시 등록
    import_cases()


if __name__ == "__main__":
    reset_cases()