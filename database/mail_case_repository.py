import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "sample_lots.db"


# ============================================================
# DB 연결
# ============================================================

def get_connection():
    """
    AeroChange SQLite DB 연결을 반환한다.
    """

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DB가 없습니다: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# Mail ↔ Case 매핑 테이블 생성
# ============================================================

def initialize_mail_case_table():
    """
    Gmail Thread와 AeroChange Case를 연결하기 위한
    테이블을 생성한다.

    이미 존재하면 그대로 유지한다.
    """

    conn = get_connection()

    try:

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mail_case_threads (
                thread_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                initial_message_id TEXT,
                sender TEXT,
                subject TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.commit()

    finally:
        conn.close()


# ============================================================
# Thread ↔ Case 저장
# ============================================================

def save_thread_case_mapping(
    thread_id,
    case_id,
    initial_message_id=None,
    sender=None,
    subject=None,
):
    """
    Gmail Thread와 Case의 연결관계를 저장한다.

    initial_message_id에는 해당 Case를 최초 생성한
    Gmail 메시지 ID를 저장한다.
    """

    initialize_mail_case_table()

    conn = get_connection()

    try:

        conn.execute(
            """
            INSERT OR REPLACE INTO mail_case_threads (
                thread_id,
                case_id,
                initial_message_id,
                sender,
                subject
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                thread_id,
                case_id,
                initial_message_id,
                sender,
                subject,
            ),
        )

        conn.commit()

    finally:
        conn.close()


# ============================================================
# Thread ID로 전체 Mail ↔ Case 정보 조회
# ============================================================

def get_mail_case_mapping_by_thread(thread_id):
    """
    Gmail thread_id를 이용하여 연결된 Case 정보를 조회한다.

    반환 예시:

    {
        "thread_id": "...",
        "case_id": "CASE-004",
        "initial_message_id": "...",
        "sender": "...",
        "subject": "...",
        "created_at": "..."
    }

    연결된 Case가 없으면 None을 반환한다.
    """

    initialize_mail_case_table()

    conn = get_connection()

    try:

        row = conn.execute(
            """
            SELECT *
            FROM mail_case_threads
            WHERE thread_id = ?
            """,
            (thread_id,),
        ).fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        conn.close()


# ============================================================
# Thread ID로 Case ID 조회
# ============================================================

def get_case_id_by_thread(thread_id):
    """
    Gmail thread_id를 이용하여 기존 Case ID를 조회한다.

    연결된 Case가 없으면 None을 반환한다.

    기존 코드와의 호환성을 위해 유지한다.
    """

    mapping = get_mail_case_mapping_by_thread(
        thread_id
    )

    if mapping is None:
        return None

    return mapping["case_id"]


# ============================================================
# Case ID로 Gmail Thread 조회
# ============================================================

def get_thread_by_case_id(case_id):
    """
    Case ID를 이용하여 연결된 Gmail Thread 정보를 조회한다.
    """

    initialize_mail_case_table()

    conn = get_connection()

    try:

        row = conn.execute(
            """
            SELECT *
            FROM mail_case_threads
            WHERE case_id = ?
            """,
            (case_id,),
        ).fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        conn.close()


# ============================================================
# 전체 Mail ↔ Case 연결 조회
# ============================================================

def get_all_mail_case_mappings():
    """
    저장된 Gmail Thread ↔ Case 연결관계를 조회한다.
    """

    initialize_mail_case_table()

    conn = get_connection()

    try:

        rows = conn.execute(
            """
            SELECT *
            FROM mail_case_threads
            ORDER BY created_at DESC
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:
        conn.close()


# ============================================================
# 직접 실행 테스트
# ============================================================

if __name__ == "__main__":

    initialize_mail_case_table()

    print(
        "mail_case_threads 테이블 준비 완료"
    )

    mappings = get_all_mail_case_mappings()

    print(
        f"현재 Mail ↔ Case 연결: {len(mappings)}건"
    )

    for mapping in mappings:
        print(mapping)