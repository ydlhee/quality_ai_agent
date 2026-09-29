import importlib.util
import json
import sqlite3
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "sample_lots.db"
OUTPUT_DIR = ROOT / "data" / "mail_pass_set"
PDF_DIR = OUTPUT_DIR / "attachments"

PART = "P-MAIL-001"
DRAWING = "DWG-MAIL-001"
SUPPLIER = "SUP-MAIL-001"
SUPPLIER_NAME = "Demo Aerospace"
PO = "PO-MAIL-001"

OLD_LOT = "LOT-MAIL-001-B"
NEW_LOT = "LOT-MAIL-001-C"

EFFECTIVITY = "2026-09-20"
MATERIAL = "AL6061"
HEAT_TREATMENT = "T6"
HEAT_NO = "HEAT-MAIL-001"

INSPECTION_ID = "INS-MAIL-001-C"


def load_parser(filename):
    path = ROOT / "parser" / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def create_pdf(filename, title, fields, schematic=False):
    path = PDF_DIR / filename
    pdf = canvas.Canvas(str(path), pagesize=A4)

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(45, 790, title)

    pdf.setFont("Helvetica", 9)
    pdf.drawString(
        45, 770,
        "AeroChange Trace AI - FICTIONAL SAMPLE - NOT FOR MANUFACTURING",
    )
    pdf.line(45, 755, 550, 755)

    y = 730
    pdf.setFont("Helvetica", 11)

    for label, value in fields:
        pdf.drawString(45, y, f"{label}: {value}")
        y -= 25

    if schematic:
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(45, 350, "PART SCHEMATIC - NOT TO SCALE")

        pdf.rect(150, 160, 270, 140)
        pdf.circle(285, 230, 35)

        pdf.setDash(5, 3)
        pdf.line(130, 230, 440, 230)
        pdf.line(285, 140, 285, 320)
        pdf.setDash()

        pdf.line(310, 255, 380, 320)
        pdf.line(380, 320, 545, 320)

        tolerance = dict(fields)["Tolerance +/- (mm)"]
        pdf.setFont("Helvetica", 10)
        pdf.drawString(
            380, 328, f"Dia. 10.00 +/- {tolerance} mm"
        )

    pdf.setFont("Helvetica", 9)
    pdf.drawString(45, 60, "Synthetic data for integration testing.")
    pdf.drawRightString(550, 60, "Page 1 of 1")
    pdf.save()

    return path


def insert_or_check(conn, table, record, key_columns):
    # 같은 키의 기존 데이터가 다르면 덮어쓰지 않고 중단한다.
    where = " AND ".join(f"{key} = ?" for key in key_columns)
    keys = tuple(record[key] for key in key_columns)

    existing = conn.execute(
        f"SELECT * FROM {table} WHERE {where}", keys
    ).fetchone()

    if existing is not None:
        for column, value in record.items():
            if existing[column] != value:
                raise ValueError(
                    f"{table}: 기존 데이터와 다릅니다. "
                    f"키={keys}, 항목={column}"
                )
        return

    columns = ", ".join(record)
    placeholders = ", ".join("?" for _ in record)

    conn.execute(
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
        tuple(record.values()),
    )


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            "기존 database/sample_lots.db가 없습니다. "
            "프로젝트 DB 초기 설정부터 실행해 주세요."
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        required_tables = {
            "parts",
            "suppliers",
            "purchase_orders",
            "lot_samples",
            "drawings",
        }
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        missing = required_tables - tables
        if missing:
            raise RuntimeError(f"필요한 DB 테이블이 없습니다: {missing}")

        drawing_parser = load_parser("drawing_parser.py")
        inspection_parser = load_parser("pdf_parser.py")
        certificate_parser = load_parser("quality_certificate_parser.py")

        PDF_DIR.mkdir(parents=True, exist_ok=True)
        drawings = []

        # 도면은 Part + Drawing + Revision 기준이다.
        # 특정 PO/Lot/Supplier를 도면의 소속으로 넣지 않는다.
        for revision, effective_from, tolerance in [
            ("B", "2026-01-01", "0.10"),
            ("C", EFFECTIVITY, "0.05"),
        ]:
            fields = [
                ("Drawing No", DRAWING),
                ("Part No", PART),
                ("Revision", revision),
                ("Effective From", effective_from),
                ("Material", MATERIAL),
                ("Heat Treatment", HEAT_TREATMENT),
                ("Characteristic ID", "DIM-001"),
                ("Characteristic Name", "Hole diameter"),
                ("Nominal (mm)", "10.00"),
                ("Tolerance +/- (mm)", tolerance),
            ]
            path = create_pdf(
                f"{DRAWING}_Rev{revision}.pdf",
                "ENGINEERING DRAWING",
                fields,
                schematic=True,
            )
            drawings.append(drawing_parser.parse_drawing_pdf(path))

        # 변경 후 Lot의 검사성적서
        inspection_fields = [
            ("Document ID", INSPECTION_ID),
            ("Part No", PART),
            ("PO No", PO),
            ("Lot No", NEW_LOT),
            ("Supplier ID", SUPPLIER),
            ("Production Date", "2026-09-22"),
            ("Drawing Revision", "C"),
            ("Characteristic ID", "DIM-001"),
            ("Nominal (mm)", "10.00"),
            ("Tolerance +/- (mm)", "0.05"),
            ("Measured (mm)", "10.02"),
            ("Heat No", HEAT_NO),
        ]
        inspection_path = create_pdf(
            f"{INSPECTION_ID}.pdf",
            "INSPECTION REPORT",
            inspection_fields,
        )
        inspection = inspection_parser.parse_inspection_pdf(
            inspection_path
        )
        if inspection["missing_fields"] or inspection["errors"]:
            raise ValueError(f"검사성적서 추출 실패: {inspection}")

        # Certificate Type은 현재 Parser가 문자열 그대로 읽는다.
        certificates = []
        for certificate_id, certificate_type, title in [
            ("MAT-MAIL-001-C", "MATERIAL", "MATERIAL CERTIFICATE"),
            (
                "HT-MAIL-001-C",
                "HEAT_TREATMENT",
                "HEAT TREATMENT CERTIFICATE",
            ),
        ]:
            fields = [
                ("Certificate ID", certificate_id),
                ("Certificate Type", certificate_type),
                ("Part No", PART),
                ("PO No", PO),
                ("Lot No", NEW_LOT),
                ("Supplier ID", SUPPLIER),
                ("Material", MATERIAL),
                ("Heat Treatment", HEAT_TREATMENT),
                ("Heat No", HEAT_NO),
                ("Drawing Revision", "C"),
            ]
            path = create_pdf(
                f"{certificate_id}.pdf", title, fields
            )
            certificates.append(
                certificate_parser.parse_certificate_pdf(path)
            )

        # 기존 DB에 기준정보와 전후 Lot을 추가한다.
        # Case와 수신 성적서는 메일 처리 과정에서 등록하도록 둔다.
        with conn:
            insert_or_check(conn, "parts", {
                "part_no": PART,
                "part_name": "Mail Test Plate",
                "drawing_no": DRAWING,
            }, ["part_no"])

            insert_or_check(conn, "suppliers", {
                "supplier_id": SUPPLIER,
                "supplier_name": SUPPLIER_NAME,
            }, ["supplier_id"])

            insert_or_check(conn, "purchase_orders", {
                "po_no": PO,
                "part_no": PART,
                "supplier_id": SUPPLIER,
                "supplier_name": SUPPLIER_NAME,
                "order_date": "2026-09-01",
            }, ["po_no"])

            for lot_no, date, revision, tolerance, measured, doc_id in [
                (
                    OLD_LOT, "2026-09-18", "B",
                    0.10, 10.08, "INS-MAIL-001-B",
                ),
                (
                    NEW_LOT, "2026-09-22", "C",
                    0.05, 10.02, INSPECTION_ID,
                ),
            ]:
                insert_or_check(conn, "lot_samples", {
                    "part_no": PART,
                    "po_no": PO,
                    "lot_no": lot_no,
                    "production_date": date,
                    "effectivity_date": EFFECTIVITY,
                    "revision": revision,
                    "document_id": doc_id,
                    "nominal_mm": 10.0,
                    "tolerance_mm": tolerance,
                    "measured_mm": measured,
                }, ["lot_no"])

            for drawing in drawings:
                insert_or_check(conn, "drawings", {
                    "drawing_no": drawing["drawing_no"],
                    "part_no": drawing["part_no"],
                    "revision": drawing["revision"],
                    "effective_from": drawing["effective_from"],
                    "drawing_json": json.dumps(
                        drawing, ensure_ascii=False, sort_keys=True
                    ),
                }, ["drawing_no", "part_no", "revision"])

        # 메일 첨부 대상과 분리한 개발자 확인용 결과
        (OUTPUT_DIR / "parser_check.json").write_text(
            json.dumps({
                "drawings": drawings,
                "inspection": inspection,
                "certificates": certificates,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        email_text = (
            f"제목: [설계변경 검증] {DRAWING} Rev.B → Rev.C / {PO}\n\n"
            f"부품: {PART}\n"
            f"협력사: {SUPPLIER} / {SUPPLIER_NAME}\n"
            f"PO: {PO}\n"
            f"설계변경: {DRAWING} Rev.B → Rev.C\n"
            f"Effectivity: {EFFECTIVITY} 생산분부터 Rev.C 적용\n"
            f"변경 전 Lot: {OLD_LOT}, 생산일 2026-09-18, Rev.B\n"
            f"변경 후 Lot: {NEW_LOT}, 생산일 2026-09-22, Rev.C\n\n"
            "변경 전후 도면과 변경 후 Lot의 검사·소재·열처리성적서를 "
            "첨부합니다. 변경 영향범위와 품질검증을 요청합니다.\n"
        )
        (OUTPUT_DIR / "email.txt").write_text(
            email_text, encoding="utf-8"
        )

        print("메일용 PDF 5개 생성 및 기존 Parser 추출 확인 완료")
        print("DB: 부품 1개 / 협력사 1개 / PO 1개 / Lot 2개 / 도면 2개")
        print(f"변경 전: {OLD_LOT} | 2026-09-18 | Rev.B | 10.08 mm")
        print(f"변경 후: {NEW_LOT} | 2026-09-22 | Rev.C | 10.02 mm")
        print("Case와 수신 성적서는 미리 등록하지 않았습니다.")
        print(f"메일 첨부 폴더: {PDF_DIR}")
        print(f"메일 제목·본문: {OUTPUT_DIR / 'email.txt'}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()