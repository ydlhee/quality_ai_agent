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


if __name__ == "__main__":
    result = get_lot("LOT-002")
    print(json.dumps(result, ensure_ascii=False, indent=2))