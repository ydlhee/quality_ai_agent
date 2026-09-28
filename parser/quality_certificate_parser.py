import json
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parent.parent

PDF_DIR = (
    ROOT
    / "data"
    / "quality_certificates"
)

OUTPUT_DIR = (
    ROOT
    / "data"
    / "parsed"
    / "quality_certificates"
)


FIELD_MAP = {
    "Certificate ID": "certificate_id",
    "Certificate Type": "certificate_type",
    "Part No": "part_no",
    "PO No": "po_no",
    "Lot No": "lot_no",
    "Supplier ID": "supplier_id",
    "Material": "material",
    "Heat Treatment": "heat_treatment",
    "Heat No": "heat_no",
}


def parse_certificate_pdf(pdf_path):
    pdf_path = Path(pdf_path)

    reader = PdfReader(pdf_path)

    values = {}
    evidence = {}

    for page_no, page in enumerate(
        reader.pages,
        start=1,
    ):
        text = page.extract_text() or ""

        for line in text.splitlines():
            label, separator, value = (
                line.partition(":")
            )

            key = FIELD_MAP.get(
                label.strip()
            )

            if not separator or key is None:
                continue

            value = value.strip()

            if not value:
                continue

            if key in values:
                raise ValueError(
                    f"{pdf_path.name}: "
                    f"중복 항목 - {key}"
                )

            values[key] = value

            evidence[key] = {
                "page": page_no,
                "text": line.strip(),
            }

    missing = [
        key
        for key in FIELD_MAP.values()
        if key not in values
    ]

    if missing:
        raise ValueError(
            f"{pdf_path.name}: "
            f"누락 항목 - {missing}"
        )

    return {
        "certificate_id":
            values["certificate_id"],
        "certificate_type":
            values["certificate_type"],
        "part_no":
            values["part_no"],
        "po_no":
            values["po_no"],
        "lot_no":
            values["lot_no"],
        "supplier_id":
            values["supplier_id"],
        "material":
            values["material"],
        "heat_treatment":
            values["heat_treatment"],
        "heat_no":
            values["heat_no"],
        "source_file":
            pdf_path.name,
        "evidence":
            evidence,
    }


def main():
    pdf_files = sorted(
        PDF_DIR.glob("*.pdf")
    )

    if not pdf_files:
        raise FileNotFoundError(
            f"품질성적서 PDF가 없습니다: "
            f"{PDF_DIR}"
        )

    certificates = [
        parse_certificate_pdf(path)
        for path in pdf_files
    ]

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIR
        / "quality_certificates_from_pdf.json"
    )

    output_path.write_text(
        json.dumps(
            certificates,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    for certificate in certificates:
        print(
            f"{certificate['source_file']} "
            f"| {certificate['certificate_type']} "
            f"| Lot: {certificate['lot_no']} "
            f"| 재질: {certificate['material']} "
            f"| 열처리: "
            f"{certificate['heat_treatment']} "
            f"| Heat: {certificate['heat_no']}"
        )

    print(
        "품질성적서 PDF 추출 결과 저장 완료"
    )


if __name__ == "__main__":
    main()