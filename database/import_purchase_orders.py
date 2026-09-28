import csv
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "purchase_orders.csv"
DB_PATH = Path(__file__).resolve().parent / "sample_lots.db"


def import_purchase_orders():
    conn = sqlite3.connect(DB_PATH)

    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS purchase_orders (
                po_no TEXT PRIMARY KEY,
                part_no TEXT NOT NULL,
                supplier_id TEXT NOT NULL,
                supplier_name TEXT NOT NULL,
                order_date TEXT NOT NULL
            )
            """
        )

        with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            rows = [
                (
                    row["po_no"],
                    row["part_no"],
                    row["supplier_id"],
                    row["supplier_name"],
                    row["order_date"],
                )
                for row in reader
            ]

        conn.executemany(
            """
            INSERT OR REPLACE INTO purchase_orders
            (
                po_no,
                part_no,
                supplier_id,
                supplier_name,
                order_date
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )

        conn.commit()

        print(f"PO {len(rows)}개 저장 완료")
        print(f"DB 위치: {DB_PATH}")

        result = conn.execute(
            "SELECT * FROM purchase_orders"
        ).fetchall()

        for row in result:
            print(
                f"{row[0]} | {row[1]} | "
                f"{row[2]} | {row[3]} | {row[4]}"
            )

    finally:
        conn.close()


if __name__ == "__main__":
    import_purchase_orders()