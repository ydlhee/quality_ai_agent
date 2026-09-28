import csv
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

CSV_PATH = (
    BASE_DIR
    / "data"
    / "required_documents.csv"
)

DB_PATH = (
    Path(__file__).resolve().parent
    / "sample_lots.db"
)


def import_required_documents():

    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"파일이 없습니다: {CSV_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)

    try:
        # =====================================
        # 1. 필수문서 기준 테이블 생성
        # =====================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS document_requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                change_type TEXT NOT NULL,
                required_document_type TEXT NOT NULL,
                description TEXT,
                UNIQUE (
                    change_type,
                    required_document_type
                )
            )
            """
        )

        # 기존 기준 초기화
        conn.execute(
            """
            DELETE FROM document_requirements
            """
        )

        # =====================================
        # 2. CSV 읽기
        # =====================================

        with open(
            CSV_PATH,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            rows = list(reader)

        # =====================================
        # 3. DB 저장
        # =====================================

        for row in rows:

            conn.execute(
                """
                INSERT INTO document_requirements (
                    change_type,
                    required_document_type,
                    description
                )
                VALUES (?, ?, ?)
                """,
                (
                    row["change_type"],
                    row["required_document_type"],
                    row["description"],
                ),
            )

        conn.commit()

        print(
            f"필수문서 기준 {len(rows)}개 저장 완료"
        )

        # =====================================
        # 4. 저장 결과 확인
        # =====================================

        saved_rows = conn.execute(
            """
            SELECT
                change_type,
                required_document_type,
                description
            FROM document_requirements
            ORDER BY id
            """
        ).fetchall()

        print()
        print("[Document Requirements]")

        for row in saved_rows:

            print(
                f"{row[0]} | "
                f"{row[1]} | "
                f"{row[2]}"
            )

    finally:
        conn.close()


if __name__ == "__main__":
    import_required_documents()