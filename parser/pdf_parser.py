import json
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = ROOT / "data" / "documents"
JSON_DIR = ROOT / "data" / "parsed"

# PDF에 적힌 항목 이름 → 코드에서 사용할 이름
FIELD_MAP = {
    "Document ID": "document_id",
    "Part No": "part_no",
    "PO No": "po_no",
    "Lot No": "lot_no",
    "Production Date": "production_date",
    "Drawing Revision": "revision",
    "Characteristic ID": "characteristic_id",
    "Nominal (mm)": "nominal_mm",
    "Tolerance +/- (mm)": "tolerance_mm",
    "Measured (mm)": "measured_mm",
}

NUMBER_FIELDS = {"nominal_mm", "tolerance_mm", "measured_mm"}


def parse_inspection_pdf(pdf_path):
    """지금 만든 샘플 검사성적서 양식에서 정보 추출."""
    pdf_path = Path(pdf_path)
    reader = PdfReader(pdf_path)

    result = {key: None for key in FIELD_MAP.values()}
    result["source_file"] = pdf_path.name
    result["evidence"] = {}
    result["errors"] = []

    for page_no, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        for line in text.splitlines():
            label, separator, value = line.partition(":")
            key = FIELD_MAP.get(label.strip())

            if not separator or key is None:
                continue

            value = value.strip()
            if not value:
                continue

            # 같은 항목이 반복되면 덮어쓰지 않고 확인 대상으로 기록
            if key in result["evidence"]:
                result["errors"].append(f"중복 항목: {key}")
                continue

            result["evidence"][key] = {
                "page": page_no,
                "text": line.strip(),
            }

            if key in NUMBER_FIELDS:
                try:
                    result[key] = float(value)
                except ValueError:
                    result["errors"].append(f"숫자 변환 실패: {key}")
            else:
                result[key] = value

    result["missing_fields"] = [
        key for key in FIELD_MAP.values()
        if result[key] is None
    ]
    return result


def main():
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"PDF 파일이 없습니다: {PDF_DIR}")

    JSON_DIR.mkdir(parents=True, exist_ok=True)

    for pdf_path in pdf_files:
        result = parse_inspection_pdf(pdf_path)
        output_path = JSON_DIR / f"{pdf_path.stem}.json"

        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(
            f"{pdf_path.name} → {output_path.name}"
            f" | Lot: {result['lot_no']}"
            f" | 측정값: {result['measured_mm']}"
        )

        if result["missing_fields"] or result["errors"]:
            print("  확인 필요:", result["missing_fields"], result["errors"])


if __name__ == "__main__":
    main()