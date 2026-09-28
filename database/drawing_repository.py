import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "sample_lots.db"


def get_drawings_by_part(part_no):
    """부품에 연결된 도면의 모든 Revision을 반환."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            "DB가 없습니다. import_drawings.py를 먼저 실행하세요."
        )

    conn = sqlite3.connect(DB_PATH)

    try:
        rows = conn.execute("""
            SELECT drawing_json
            FROM drawings
            WHERE part_no = ?
            ORDER BY drawing_no, effective_from, revision
        """, (part_no,)).fetchall()

        return [json.loads(row[0]) for row in rows]
    finally:
        conn.close()


if __name__ == "__main__":
    drawings = get_drawings_by_part("P-001")

    print(f"조회된 도면 기준: {len(drawings)}개")

    for drawing in drawings:
        print(
            f"{drawing['drawing_no']} | Rev.{drawing['revision']}"
            f" | 적용 시작일: {drawing['effective_from']}"
        )

        for item in drawing["characteristics"]:
            print(
                f"  {item['characteristic_id']}: "
                f"{item['nominal_mm']:.2f} "
                f"±{item['tolerance_mm']:.2f} mm"
            )