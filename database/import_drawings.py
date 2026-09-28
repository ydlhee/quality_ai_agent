import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = ROOT / "data" / "parsed" / "drawings" / "drawings_from_pdf.json"
DB_PATH = ROOT / "database" / "sample_lots.db"


def main():
    drawings = json.loads(
        JSON_PATH.read_text(encoding="utf-8-sig")
    )

    conn = sqlite3.connect(DB_PATH)

    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS drawings (
                    drawing_no TEXT NOT NULL,
                    part_no TEXT NOT NULL,
                    revision TEXT NOT NULL,
                    effective_from TEXT NOT NULL,
                    drawing_json TEXT NOT NULL,
                    PRIMARY KEY (drawing_no, part_no, revision)
                )
            """)

            for drawing in drawings:
                conn.execute("""
                    INSERT INTO drawings (
                        drawing_no, part_no, revision,
                        effective_from, drawing_json
                    )
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(drawing_no, part_no, revision)
                    DO UPDATE SET
                        effective_from = excluded.effective_from,
                        drawing_json = excluded.drawing_json
                """, (
                    drawing["drawing_no"],
                    drawing["part_no"],
                    drawing["revision"],
                    drawing["effective_from"],
                    json.dumps(drawing, ensure_ascii=False),
                ))

        print(f"도면 기준 {len(drawings)}개 저장 완료")

        rows = conn.execute("""
            SELECT drawing_no, revision, effective_from
            FROM drawings
            ORDER BY drawing_no, part_no, effective_from
        """).fetchall()

        for drawing_no, revision, effective_from in rows:
            print(
                f"{drawing_no} | Rev.{revision}"
                f" | 적용 시작일: {effective_from}"
            )

    finally:
        conn.close()


if __name__ == "__main__":
    main()