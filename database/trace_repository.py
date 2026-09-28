import json
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "sample_lots.db"


def parse_json(value):
    """DB에 저장된 JSON 문자열을 Python 객체로 변환."""
    if not value:
        return None

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def get_trace_by_part(part_no):
    """
    Part 번호를 기준으로
    Drawing → PO → Supplier → Lot → Document
    정보를 한 번에 조회한다.
    """

    if not DB_PATH.exists():
        raise FileNotFoundError(
            "DB가 없습니다. 먼저 데이터 import 파일들을 실행하세요."
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        # 1. 도면 조회
        drawing_rows = conn.execute(
            """
            SELECT drawing_json
            FROM drawings
            WHERE part_no = ?
            ORDER BY effective_from, revision
            """,
            (part_no,),
        ).fetchall()

        drawings = [
            parse_json(row["drawing_json"])
            for row in drawing_rows
        ]

        # 2. PO 조회
        po_rows = conn.execute(
            """
            SELECT *
            FROM purchase_orders
            WHERE part_no = ?
            ORDER BY order_date
            """,
            (part_no,),
        ).fetchall()

        purchase_orders = []

        for po_row in po_rows:
            po = dict(po_row)

            # 3. 해당 PO의 Lot 조회
            lot_rows = conn.execute(
                """
                SELECT *
                FROM lot_samples
                WHERE po_no = ?
                ORDER BY production_date
                """,
                (po["po_no"],),
            ).fetchall()

            lots = []

            for lot_row in lot_rows:
                lot = dict(lot_row)

                # 4. 해당 Lot의 검사성적서 조회
                document_rows = conn.execute(
                    """
                    SELECT *
                    FROM inspection_documents
                    WHERE lot_no = ?
                    """,
                    (lot["lot_no"],),
                ).fetchall()

                documents = []

                for document_row in document_rows:
                    document = dict(document_row)

                    if "extracted_json" in document:
                        document["extracted_json"] = parse_json(
                            document["extracted_json"]
                        )

                    documents.append(document)

                lot["documents"] = documents
                lots.append(lot)

            po["lots"] = lots
            purchase_orders.append(po)

        return {
            "part_no": part_no,
            "drawings": drawings,
            "purchase_orders": purchase_orders,
        }

    finally:
        conn.close()


if __name__ == "__main__":
    result = get_trace_by_part("P-002")

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )