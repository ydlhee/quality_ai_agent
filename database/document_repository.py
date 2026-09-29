import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "sample_lots.db"


def get_documents_by_lot(lot_no):
    """Lot에 연결된 검사성적서들을 반환. 없으면 빈 목록 반환."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            "DB가 없습니다. 데이터 저장 코드를 먼저 실행하세요."
        )

    conn = sqlite3.connect(DB_PATH)

    try:
        rows = conn.execute("""
            SELECT extracted_json
            FROM inspection_documents
            WHERE lot_no = ?
            ORDER BY source_file
        """, (lot_no,)).fetchall()

        return [json.loads(row[0]) for row in rows]
    finally:
        conn.close()


if __name__ == "__main__":
    documents = get_documents_by_lot("LOT-003")

    print(f"조회된 검사성적서: {len(documents)}개")

    for document in documents:
        evidence = document.get("evidence", {}).get("measured_mm", {})

        print(f"문서 ID: {document.get('document_id')}")
        print(f"Lot 번호: {document.get('lot_no')}")
        print(f"측정값: {document.get('measured_mm')} mm")
        print(f"근거 파일: {document.get('source_file')}")
        print(f"근거 페이지: {evidence.get('page')}")
        print(f"원문: {evidence.get('text')}")
        print(f"누락 항목: {document.get('missing_fields')}")
        print(f"추출 오류: {document.get('errors')}")