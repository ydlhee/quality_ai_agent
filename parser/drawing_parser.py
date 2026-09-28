import json
import math
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = ROOT / "data" / "drawing_pdfs"
OUTPUT_DIR = ROOT / "data" / "parsed" / "drawings"

FIELD_MAP = {
    "Drawing No": "drawing_no",
    "Part No": "part_no",
    "Revision": "revision",
    "Effective From": "effective_from",
    "Material": "material",
    "Heat Treatment": "heat_treatment",
    "Characteristic ID": "characteristic_id",
    "Characteristic Name": "name",
    "Nominal (mm)": "nominal_mm",
    "Tolerance +/- (mm)": "tolerance_mm",
}


def parse_drawing_pdf(pdf_path):
    pdf_path = Path(pdf_path)
    reader = PdfReader(pdf_path)
    values = {}
    evidence = {}

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

            if key in values:
                raise ValueError(
                    f"{pdf_path.name}: 중복 항목 확인 필요 - {key}"
                )

            values[key] = value
            evidence[key] = {
                "page": page_no,
                "text": line.strip(),
            }

    missing = [
        key for key in FIELD_MAP.values()
        if key not in values
    ]

    if missing:
        raise ValueError(
            f"{pdf_path.name}: 누락 항목 - {missing}"
        )

    for key in ("nominal_mm", "tolerance_mm"):
        values[key] = float(values[key])

        if (
            not math.isfinite(values[key])
            or values[key] < 0
        ):
            raise ValueError(
                f"{pdf_path.name}: 잘못된 숫자 - {key}"
            )

    return {
        "drawing_no": values["drawing_no"],
        "part_no": values["part_no"],
        "revision": values["revision"],
        "effective_from": values["effective_from"],
        "material": values["material"],
        "heat_treatment": values["heat_treatment"],
        "characteristics": [
            {
                "characteristic_id": values["characteristic_id"],
                "name": values["name"],
                "nominal_mm": values["nominal_mm"],
                "tolerance_mm": values["tolerance_mm"],
            }
        ],
        "source_file": pdf_path.name,
        "evidence": evidence,
    }


def main():
    pdf_files = sorted(
        PDF_DIR.glob("*.pdf")
    )

    if not pdf_files:
        raise FileNotFoundError(
            f"도면 PDF가 없습니다: {PDF_DIR}"
        )

    # 모든 PDF를 성공적으로 읽은 뒤 결과 저장
    drawings = [
        parse_drawing_pdf(path)
        for path in pdf_files
    ]

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIR
        / "drawings_from_pdf.json"
    )

    output_path.write_text(
        json.dumps(
            drawings,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    for drawing in drawings:
        item = drawing["characteristics"][0]

        print(
            f"{drawing['source_file']} "
            f"| Rev.{drawing['revision']} "
            f"| 재질: {drawing['material']} "
            f"| 열처리: {drawing['heat_treatment']} "
            f"| 공차: ±{item['tolerance_mm']:.2f} mm "
            f"| 적용일: {drawing['effective_from']}"
        )

    print(
        "도면 PDF 추출 결과 저장 완료"
    )


if __name__ == "__main__":
    main()