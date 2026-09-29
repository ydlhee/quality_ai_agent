import csv
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

PARTS_CSV = BASE_DIR / "data" / "parts.csv"
SUPPLIERS_CSV = BASE_DIR / "data" / "suppliers.csv"

DB_PATH = Path(__file__).resolve().parent / "sample_lots.db"


def import_master_data():
    conn = sqlite3.connect(DB_PATH)

    try:
        # Part 테이블
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS parts (
                part_no TEXT PRIMARY KEY,
                part_name TEXT NOT NULL,
                drawing_no TEXT NOT NULL
            )
            """
        )

        # Supplier 테이블
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS suppliers (
                supplier_id TEXT PRIMARY KEY,
                supplier_name TEXT NOT NULL
            )
            """
        )

        # Parts CSV 읽기
        with open(PARTS_CSV, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            part_rows = [
                (
                    row["part_no"],
                    row["part_name"],
                    row["drawing_no"],
                )
                for row in reader
            ]

        conn.executemany(
            """
            INSERT OR REPLACE INTO parts
            (part_no, part_name, drawing_no)
            VALUES (?, ?, ?)
            """,
            part_rows,
        )

        # Suppliers CSV 읽기
        with open(SUPPLIERS_CSV, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            supplier_rows = [
                (
                    row["supplier_id"],
                    row["supplier_name"],
                )
                for row in reader
            ]

        conn.executemany(
            """
            INSERT OR REPLACE INTO suppliers
            (supplier_id, supplier_name)
            VALUES (?, ?)
            """,
            supplier_rows,
        )

        conn.commit()

        print(f"Part {len(part_rows)}개 저장 완료")
        print(f"Supplier {len(supplier_rows)}개 저장 완료")
        print(f"DB 위치: {DB_PATH}")

        print("\n[Parts]")
        for row in conn.execute("SELECT * FROM parts"):
            print(f"{row[0]} | {row[1]} | {row[2]}")

        print("\n[Suppliers]")
        for row in conn.execute("SELECT * FROM suppliers"):
            print(f"{row[0]} | {row[1]}")

    finally:
        conn.close()


if __name__ == "__main__":
    import_master_data()