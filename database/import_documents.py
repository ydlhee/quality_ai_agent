import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSON_DIR = ROOT / "data" / "parsed"
DB_PATH = ROOT / "database" / "sample_lots.db"


def main():
    json_files = sorted(JSON_DIR.glob("*.json"))
    if not json_files:
        raise FileNotFoundError("먼저 pdf_parser.py를 실행하세요.")

    conn = sqlite3.connect(DB_PATH)

    try:
        with conn:
            # PDF에서 추출한 정보를 보관할 별도 테이블
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inspection_documents (
                    source_file TEXT PRIMARY KEY,
                    document_id TEXT,
                    lot_no TEXT,
                    part_no TEXT,
                    extracted_json TEXT NOT NULL
                )
            """)

            for json_path in json_files:
                data = json.loads(
                    json_path.read_text(encoding="utf-8")
                )

                # 값, 근거 페이지, 누락·오류 정보를 모두 보관
                payload = json.dumps(data, ensure_ascii=False)

                conn.execute("""
                    INSERT INTO inspection_documents (
                        source_file, document_id, lot_no,
                        part_no, extracted_json
                    )
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(source_file) DO UPDATE SET
                        document_id = excluded.document_id,
                        lot_no = excluded.lot_no,
                        part_no = excluded.part_no,
                        extracted_json = excluded.extracted_json
                """, (
                    data["source_file"],
                    data.get("document_id"),
                    data.get("lot_no"),
                    data.get("part_no"),
                    payload,
                ))

        print(f"검사성적서 {len(json_files)}개 저장 완료")

        rows = conn.execute("""
            SELECT document_id, lot_no, source_file
            FROM inspection_documents
            ORDER BY source_file
        """).fetchall()

        for document_id, lot_no, source_file in rows:
            print(f"{document_id} | {lot_no} | {source_file}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()