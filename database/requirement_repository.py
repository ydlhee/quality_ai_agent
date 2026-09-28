import sqlite3
from pathlib import Path


DB_PATH = (
    Path(__file__).resolve().parent
    / "sample_lots.db"
)


def get_all_document_requirements():
    """
    전체 필수문서 기준 조회
    """

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute(
            """
            SELECT
                change_type,
                required_document_type,
                description
            FROM document_requirements
            ORDER BY id
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:
        conn.close()


def get_required_documents(change_types):
    """
    설계변경 유형 목록을 받아
    필요한 문서 기준만 조회한다.

    예:
    [
        "REVISION_CHANGE",
        "TOLERANCE_CHANGE",
        "MATERIAL_CHANGE"
    ]
    """

    if not change_types:
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        placeholders = ",".join(
            "?"
            for _ in change_types
        )

        rows = conn.execute(
            f"""
            SELECT
                change_type,
                required_document_type,
                description
            FROM document_requirements
            WHERE change_type IN ({placeholders})
            ORDER BY id
            """,
            change_types,
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:
        conn.close()


if __name__ == "__main__":

    print("[전체 필수문서 기준]")

    for item in get_all_document_requirements():
        print(
            item["change_type"],
            "→",
            item["required_document_type"],
        )

    print()
    print("[P-001 Rev.B → Rev.C 예시]")

    requirements = get_required_documents(
        [
            "REVISION_CHANGE",
            "TOLERANCE_CHANGE",
            "MATERIAL_CHANGE",
        ]
    )

    for item in requirements:
        print(
            item["change_type"],
            "→",
            item["required_document_type"],
            "|",
            item["description"],
        )