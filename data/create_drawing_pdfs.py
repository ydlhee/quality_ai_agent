from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


DATA_DIR = Path(__file__).resolve().parent
PDF_DIR = DATA_DIR / "drawing_pdfs"

PDF_DIR.mkdir(parents=True, exist_ok=True)


drawings = [
    {
        "drawing_no": "DWG-001",
        "part_no": "P-001",
        "revision": "B",
        "effective_from": "2026-01-01",
        "characteristic_id": "DIM-001",
        "name": "Hole diameter",
        "nominal_mm": "10.00",
        "tolerance_mm": "0.10",
    },
    {
        "drawing_no": "DWG-001",
        "part_no": "P-001",
        "revision": "C",
        "effective_from": "2026-09-20",
        "characteristic_id": "DIM-001",
        "name": "Hole diameter",
        "nominal_mm": "10.00",
        "tolerance_mm": "0.05",
    },
    {
        "drawing_no": "DWG-002",
        "part_no": "P-002",
        "revision": "B",
        "effective_from": "2026-01-01",
        "characteristic_id": "DIM-001",
        "name": "Hole diameter",
        "nominal_mm": "20.00",
        "tolerance_mm": "0.20",
    },
    {
        "drawing_no": "DWG-002",
        "part_no": "P-002",
        "revision": "C",
        "effective_from": "2026-09-20",
        "characteristic_id": "DIM-001",
        "name": "Hole diameter",
        "nominal_mm": "20.00",
        "tolerance_mm": "0.10",
    },
]


for drawing in drawings:
    file_name = (
        f"{drawing['drawing_no']}_Rev{drawing['revision']}.pdf"
    )

    pdf_path = PDF_DIR / file_name
    pdf = canvas.Canvas(str(pdf_path), pagesize=A4)

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, 790, "ENGINEERING DRAWING")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        50,
        765,
        "AeroChange Trace AI - SAMPLE DATA ONLY",
    )

    pdf.line(50, 750, 545, 750)

    fields = [
        ("Drawing No", drawing["drawing_no"]),
        ("Part No", drawing["part_no"]),
        ("Revision", drawing["revision"]),
        ("Effective From", drawing["effective_from"]),
        (
            "Characteristic ID",
            drawing["characteristic_id"],
        ),
        (
            "Characteristic Name",
            drawing["name"],
        ),
        ("Nominal (mm)", drawing["nominal_mm"]),
        (
            "Tolerance +/- (mm)",
            drawing["tolerance_mm"],
        ),
    ]

    pdf.setFont("Helvetica", 12)
    y = 715

    for label, value in fields:
        pdf.drawString(50, y, f"{label}: {value}")
        y -= 32

    pdf.setFont("Helvetica", 9)
    pdf.drawString(
        50,
        60,
        "Fictional drawing data for development.",
    )
    pdf.drawRightString(545, 60, "Page 1 of 1")

    pdf.save()

    print(f"생성 완료: {file_name}")


print(f"총 {len(drawings)}개 도면 PDF 생성 완료")