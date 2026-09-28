import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "sample_lots.db"


def get_lot(lot_no):
    """Lot 번호로 데이터를 조회. 없으면 None 반환."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            "DB가 없습니다. import_lots.py를 먼저 실행하세요."
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        row = conn.execute(
            "SELECT * FROM lot_samples WHERE lot_no = ?",
            (lot_no,),
        ).fetchone()

        return dict(row) if row is not None else None
    finally:
        conn.close()
def get_lots_by_part(part_no):
    """Part 번호에 연결된 모든 Lot을 조회."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            "DB가 없습니다. import_lots.py를 먼저 실행하세요."
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute(
            """
            SELECT *
            FROM lot_samples
            WHERE part_no = ?
            ORDER BY production_date
            """,
            (part_no,),
        ).fetchall()

        return [dict(row) for row in rows]
    finally:
        conn.close()

if __name__ == "__main__":
    results = get_lots_by_part("P-001")
    print(json.dumps(results, ensure_ascii=False, indent=2))