import json
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "sample_lots.db"


def get_po_with_lots(po_no):
    """PO 번호로 발주정보와 연결된 Lot 목록을 조회한다."""

    if not DB_PATH.exists():
        raise FileNotFoundError(
            "DB가 없습니다. import_purchase_orders.py를 먼저 실행하세요."
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        po = conn.execute(
            """
            SELECT *
            FROM purchase_orders
            WHERE po_no = ?
            """,
            (po_no,),
        ).fetchone()

        if po is None:
            return None

        lots = conn.execute(
            """
            SELECT *
            FROM lot_samples
            WHERE po_no = ?
            ORDER BY production_date
            """,
            (po_no,),
        ).fetchall()

        result = dict(po)
        result["lots"] = [dict(lot) for lot in lots]

        return result

    finally:
        conn.close()


if __name__ == "__main__":
    result = get_po_with_lots("PO-001")
    print(json.dumps(result, ensure_ascii=False, indent=2))