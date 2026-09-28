import json
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

JSON_PATH = (
    BASE_DIR
    / "data"
    / "parsed"
    / "quality_certificates"
    / "quality_certificates_from_pdf.json"
)

DB_PATH = Path(__file__).resolve().parent / "sample_lots.db"


def import_quality_certificates():
    if not JSON_PATH.exists():
        raise FileNotFoundError(
            "품질성적서 추출 JSON이 없습니다. "
            "quality_certificate_parser.py를 먼저 실행하세요."
        )

    certificates = json.loads(
        JSON_PATH.read_text(
            encoding="utf-8"
        )
    )

    conn = sqlite3.connect(DB_PATH)

    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quality_certificates (
                certificate_id TEXT PRIMARY KEY,
                certificate_type TEXT NOT NULL,
                part_no TEXT NOT NULL,
                po_no TEXT NOT NULL,
                lot_no TEXT NOT NULL,
                supplier_id TEXT NOT NULL,
                material TEXT NOT NULL,
                heat_treatment TEXT NOT NULL,
                heat_no TEXT NOT NULL,
                source_file TEXT NOT NULL,
                extracted_json TEXT NOT NULL
            )
            """
        )

        rows = []

        for certificate in certificates:
            rows.append(
                (
                    certificate["certificate_id"],
                    certificate["certificate_type"],
                    certificate["part_no"],
                    certificate["po_no"],
                    certificate["lot_no"],
                    certificate["supplier_id"],
                    certificate["material"],
                    certificate["heat_treatment"],
                    certificate["heat_no"],
                    certificate["source_file"],
                    json.dumps(
                        certificate,
                        ensure_ascii=False,
                    ),
                )
            )

        conn.executemany(
            """
            INSERT OR REPLACE INTO quality_certificates
            (
                certificate_id,
                certificate_type,
                part_no,
                po_no,
                lot_no,
                supplier_id,
                material,
                heat_treatment,
                heat_no,
                source_file,
                extracted_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

        conn.commit()

        print(
            f"품질성적서 {len(rows)}개 저장 완료"
        )

        print("\n[Quality Certificates]")

        result = conn.execute(
            """
            SELECT
                certificate_id,
                certificate_type,
                lot_no,
                material,
                heat_treatment,
                heat_no
            FROM quality_certificates
            ORDER BY certificate_id
            """
        ).fetchall()

        for row in result:
            print(
                f"{row[0]} | "
                f"{row[1]} | "
                f"{row[2]} | "
                f"{row[3]} | "
                f"{row[4]} | "
                f"{row[5]}"
            )

    finally:
        conn.close()


if __name__ == "__main__":
    import_quality_certificates()