import csv
import sqlite3
from pathlib import Path

# 프로젝트 폴더 기준으로 파일 위치 지정
ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "lots.csv"
DB_PATH = ROOT / "database" / "sample_lots.db"


def main():
    # CSV 파일 읽기
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    # 숫자 항목을 숫자로 변환
    records = [
        (
            row["part_no"],
            row["po_no"],
            row["lot_no"],
            row["production_date"],
            row["effectivity_date"],
            row["revision"],
            row["document_id"],
            float(row["nominal_mm"]),
            float(row["tolerance_mm"]),
            float(row["measured_mm"]),
        )
        for row in rows
    ]

    # DB 연결: 파일이 없으면 자동 생성
    conn = sqlite3.connect(DB_PATH)

    try:
        with conn:
            # 현재 CSV를 저장할 샘플 테이블 생성
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lot_samples (
                    part_no TEXT NOT NULL,
                    po_no TEXT NOT NULL,
                    lot_no TEXT PRIMARY KEY,
                    production_date TEXT NOT NULL,
                    effectivity_date TEXT NOT NULL,
                    revision TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    nominal_mm REAL NOT NULL,
                    tolerance_mm REAL NOT NULL,
                    measured_mm REAL NOT NULL
                )
            """)

            # 같은 Lot가 있으면 갱신하여 중복 저장 방지
            conn.executemany("""
                INSERT INTO lot_samples (
                    part_no, po_no, lot_no,
                    production_date, effectivity_date,
                    revision, document_id,
                    nominal_mm, tolerance_mm, measured_mm
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(lot_no) DO UPDATE SET
                    part_no = excluded.part_no,
                    po_no = excluded.po_no,
                    production_date = excluded.production_date,
                    effectivity_date = excluded.effectivity_date,
                    revision = excluded.revision,
                    document_id = excluded.document_id,
                    nominal_mm = excluded.nominal_mm,
                    tolerance_mm = excluded.tolerance_mm,
                    measured_mm = excluded.measured_mm
            """, records)

        print(f"CSV {len(records)}개 행 저장 완료")
        print(f"DB 위치: {DB_PATH}")

        # DB에 실제로 저장된 결과 조회
        saved_rows = conn.execute("""
            SELECT lot_no, revision, measured_mm
            FROM lot_samples
            ORDER BY lot_no
        """).fetchall()

        for lot_no, revision, measured_mm in saved_rows:
            print(f"{lot_no} | Rev.{revision} | {measured_mm:.2f} mm")

    finally:
        conn.close()


if __name__ == "__main__":
    main()