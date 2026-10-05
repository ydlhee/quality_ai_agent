import sqlite3
from pathlib import Path


DB_PATH = (
    Path(__file__).resolve().parent
    / "mail_outbound.db"
)


def get_connection():
    """
    후속조치 Gmail 발송이력 전용 DB 연결.
    품질검증 sample_lots.db와 완전히 분리한다.
    """

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    return conn


def initialize_outbound_mail_table():
    """
    후속조치 Gmail 발송이력 테이블 생성.
    """

    conn = get_connection()

    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS outbound_mail_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                case_id TEXT NOT NULL,
                lot_id TEXT NOT NULL,
                action_type TEXT NOT NULL,

                sender_email TEXT,
                recipient_email TEXT,

                subject TEXT,
                body TEXT,

                gmail_message_id TEXT,
                gmail_thread_id TEXT,

                status TEXT NOT NULL DEFAULT 'SENT',

                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (
                    case_id,
                    lot_id,
                    action_type
                )
            )
            """
        )

        conn.commit()

    finally:
        conn.close()


def save_outbound_mail(
    case_id,
    lot_id,
    action_type,
    sender_email,
    recipient_email,
    subject,
    body,
    gmail_message_id=None,
    gmail_thread_id=None,
):
    """
    Gmail API 발송 성공 후 발송이력을 저장한다.

    동일 Case + Lot + action_type의 메일은
    한 번만 기록하여 중복 발송을 방지한다.
    """

    initialize_outbound_mail_table()

    conn = get_connection()

    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO outbound_mail_history (
                case_id,
                lot_id,
                action_type,
                sender_email,
                recipient_email,
                subject,
                body,
                gmail_message_id,
                gmail_thread_id,
                status,
                sent_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, 'SENT',
                CURRENT_TIMESTAMP
            )
            """,
            (
                case_id,
                lot_id,
                action_type,
                sender_email,
                recipient_email,
                subject,
                body,
                gmail_message_id,
                gmail_thread_id,
            ),
        )

        conn.commit()

    finally:
        conn.close()


def get_outbound_mail(
    case_id,
    lot_id,
    action_type,
):
    """
    특정 Case/Lot 후속조치 메일의
    발송이력을 조회한다.
    """

    initialize_outbound_mail_table()

    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT *
            FROM outbound_mail_history
            WHERE case_id = ?
              AND lot_id = ?
              AND action_type = ?
              AND status = 'SENT'
            ORDER BY sent_at DESC
            LIMIT 1
            """,
            (
                case_id,
                lot_id,
                action_type,
            ),
        ).fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        conn.close()


def get_outbound_mails_by_case(case_id):
    """
    Case별 전체 발송이력 조회.
    """

    initialize_outbound_mail_table()

    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT *
            FROM outbound_mail_history
            WHERE case_id = ?
            ORDER BY sent_at DESC
            """,
            (case_id,),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:
        conn.close()


if __name__ == "__main__":

    initialize_outbound_mail_table()

    print(
        f"발송이력 DB 준비 완료: {DB_PATH}"
    )
