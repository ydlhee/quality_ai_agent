import csv
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


DATA_DIR = Path(__file__).resolve().parent
CSV_PATH = DATA_DIR / "quality_certificates.csv"
PDF_DIR = DATA_DIR / "quality_certificates"

PDF_DIR.mkdir(parents=True, exist_ok=True)


with CSV_PATH.open(
    encoding="utf-8-sig",
    newline="",
) as file:
    certificates = list(csv.DictReader(file))


for certificate in certificates:
    certificate_id = certificate["certificate_id"]
    certificate_type = certificate["certificate_type"]

    pdf_path = PDF_DIR / f"{certificate_id}.pdf"

    pdf = canvas.Canvas(
        str(pdf_path),
        pagesize=A4,
    )

    if certificate_type == "MATERIAL":
        title = "MATERIAL CERTIFICATE"
    elif certificate_type == "HEAT_TREATMENT":
        title = "HEAT TREATMENT CERTIFICATE"
    else:
        title = "QUALITY CERTIFICATE"

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(
        50,
        790,
        title,
    )

    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        50,
        765,
        "AeroChange Trace AI - SAMPLE DATA ONLY",
    )

    pdf.line(
        50,
        750,
        545,
        750,
    )

    fields = [
        (
            "Certificate ID",
            certificate["certificate_id"],
        ),
        (
            "Certificate Type",
            certificate["certificate_type"],
        ),
        (
            "Part No",
            certificate["part_no"],
        ),
        (
            "PO No",
            certificate["po_no"],
        ),
        (
            "Lot No",
            certificate["lot_no"],
        ),
        (
            "Supplier ID",
            certificate["supplier_id"],
        ),
        (
            "Material",
            certificate["material"],
        ),
        (
            "Heat Treatment",
            certificate["heat_treatment"],
        ),
        (
            "Heat No",
            certificate["heat_no"],
        ),
    ]

    pdf.setFont("Helvetica", 12)

    y = 715

    for label, value in fields:
        pdf.drawString(
            50,
            y,
            f"{label}: {value}",
        )
        y -= 32

    pdf.setFont("Helvetica", 9)

    pdf.drawString(
        50,
        60,
        "Fictional quality certificate for development.",
    )

    pdf.drawRightString(
        545,
        60,
        "Page 1 of 1",
    )

    pdf.save()

    print(
        f"생성 완료: {pdf_path.name}"
    )


print(
    f"총 {len(certificates)}개 품질성적서 PDF 생성 완료"
)