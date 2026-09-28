import json
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

DATA_DIR = Path(__file__).resolve().parent
JSON_PATH = DATA_DIR / "drawings.json"
OUTPUT_DIR = DATA_DIR / "drawing_pdfs"


def main():
    drawings = json.loads(
        JSON_PATH.read_text(encoding="utf-8-sig")
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for drawing in drawings:
        filename = (
            f"{drawing['drawing_no']}"
            f"_Rev{drawing['revision']}.pdf"
        )
        pdf_path = OUTPUT_DIR / filename
        pdf = canvas.Canvas(str(pdf_path), pagesize=A4)

        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(50, 790, "SAMPLE ENGINEERING DRAWING")

        pdf.setFont("Helvetica", 10)
        pdf.drawString(50, 765, "AeroChange Trace AI - NOT FOR MANUFACTURING")
        pdf.line(50, 750, 545, 750)

        fields = [
            ("Drawing No", drawing["drawing_no"]),
            ("Part No", drawing["part_no"]),
            ("Revision", drawing["revision"]),
            ("Effective From", drawing["effective_from"]),
        ]

        pdf.setFont("Helvetica", 12)
        y = 720

        for label, value in fields:
            pdf.drawString(50, y, f"{label}: {value}")
            y -= 28

        # 현재 샘플의 품질특성은 구멍 지름 1개
        item = drawing["characteristics"][0]

        characteristic_fields = [
            ("Characteristic ID", item["characteristic_id"]),
            ("Characteristic Name", item["name"]),
            ("Nominal (mm)", f"{item['nominal_mm']:.2f}"),
            ("Tolerance +/- (mm)", f"{item['tolerance_mm']:.2f}"),
        ]

        y -= 15
        for label, value in characteristic_fields:
            pdf.drawString(50, y, f"{label}: {value}")
            y -= 28

        # 형상 이해를 돕는 개략도: 실제 치수 비례 도면은 아님
        pdf.rect(170, 190, 240, 150)
        pdf.circle(290, 265, 35)

        pdf.setDash(4, 3)
        pdf.line(240, 265, 340, 265)
        pdf.line(290, 215, 290, 315)
        pdf.setDash()

        pdf.setFont("Helvetica", 10)
        pdf.drawCentredString(290, 165, "DIM-001: Hole diameter")
        pdf.drawCentredString(290, 145, "Schematic only - not to scale")

        pdf.setFont("Helvetica", 9)
        pdf.drawString(50, 60, "Fictional drawing for development.")
        pdf.drawRightString(545, 60, "Page 1 of 1")

        pdf.save()
        print(f"생성 완료: {filename}")

    print(f"총 {len(drawings)}개 도면 PDF 생성 완료")


if __name__ == "__main__":
    main()