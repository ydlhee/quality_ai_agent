import csv
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

DATA_DIR = Path(__file__).resolve().parent
CSV_PATH = DATA_DIR / "lots.csv"
PDF_DIR = DATA_DIR / "documents"

# PDF를 저장할 폴더 자동 생성
PDF_DIR.mkdir(parents=True, exist_ok=True)

# 기존 CSV 읽기
with CSV_PATH.open(encoding="utf-8-sig", newline="") as file:
    lots = list(csv.DictReader(file))

for lot in lots:
    pdf_path = PDF_DIR / f"{lot['document_id']}.pdf"
    pdf = canvas.Canvas(str(pdf_path), pagesize=A4)

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, 790, "INSPECTION REPORT")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, 765, "AeroChange Trace AI - SAMPLE DATA ONLY")
    pdf.line(50, 750, 545, 750)

    fields = [
        ("Document ID", lot["document_id"]),
        ("Part No", lot["part_no"]),
        ("PO No", lot["po_no"]),
        ("Lot No", lot["lot_no"]),
        ("Production Date", lot["production_date"]),
        ("Drawing Revision", lot["revision"]),
        ("Characteristic ID", "DIM-001"),
        ("Nominal (mm)", lot["nominal_mm"]),
        ("Tolerance +/- (mm)", lot["tolerance_mm"]),
        ("Measured (mm)", lot["measured_mm"]),
    ]

    pdf.setFont("Helvetica", 12)
    y = 715

    for label, value in fields:
        pdf.drawString(50, y, f"{label}: {value}")
        y -= 32

    pdf.setFont("Helvetica", 9)
    pdf.drawString(50, 60, "Fictional inspection data for development.")
    pdf.drawRightString(545, 60, "Page 1 of 1")

    pdf.save()
    print(f"생성 완료: {pdf_path.name}")

print(f"총 {len(lots)}개 PDF 생성 완료")