import importlib.util
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "sample_lots.db"
OUTPUT_DIR = ROOT / "data" / "mail_hold_set"

PART = "P-MAIL-HOLD-001"
DRAWING = "DWG-MAIL-HOLD-001"
PO = "PO-MAIL-HOLD-001"
SUPPLIER = "SUP-MAIL-HOLD-001"
SUPPLIER_NAME = "Demo Hold Aerospace"

OLD_LOT = "LOT-MAIL-HOLD-001-B"
NEW_LOT = "LOT-MAIL-HOLD-001-C"
INSPECTION_ID = "INS-MAIL-HOLD-001-C"

EFFECTIVITY = "2026-09-20"
HEAT_NO = "HEAT-MAIL-HOLD-001"


def load_module(path):
    spec = importlib.util.spec_from_file_location(
        "fixture_" + path.stem, path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    if not DB_PATH.is_file():
        raise FileNotFoundError(
            "기존 database/sample_lots.db가 없습니다."
        )

    helper = load_module(
        ROOT / "data" / "create_mail_pass_set.py"
    )
    drawing_parser = load_module(
        ROOT / "parser" / "drawing_parser.py"
    )
    inspection_parser = load_module(
        ROOT / "parser" / "pdf_parser.py"
    )
    certificate_parser = load_module(
        ROOT / "parser" / "quality_certificate_parser.py"
    )

    initial_dir = OUTPUT_DIR / "initial_attachments"
    supplemental_dir = OUTPUT_DIR / "supplemental_attachments"

    initial_dir.mkdir(parents=True, exist_ok=True)
    supplemental_dir.mkdir(parents=True, exist_ok=True)

    initial_files = {
        f"{DRAWING}_RevB.pdf",
        f"{DRAWING}_RevC.pdf",
        "MAT-MAIL-HOLD-001-C.pdf",
        "HT-MAIL-HOLD-001-C.pdf",
    }
    supplemental_files = {f"{INSPECTION_ID}.pdf"}

    # 이전 실행의 다른 파일이 섞여서 잘못 첨부되는 것을 방지한다.
    for folder, allowed in (
        (initial_dir, initial_files),
        (supplemental_dir, supplemental_files),
    ):
        extras = {
            path.name for path in folder.iterdir()
            if path.is_file()
        } - allowed

        if extras:
            raise ValueError(
                f"{folder}에 예상하지 않은 파일이 있습니다: "
                f"{sorted(extras)}"
            )

    helper.PDF_DIR = initial_dir
    drawings = []

    # 최초 메일: 변경 전/후 도면
    for revision, effective_from, tolerance in (
        ("B", "2026-01-01", "0.10"),
        ("C", EFFECTIVITY, "0.05"),
    ):
        fields = [
            ("Drawing No", DRAWING),
            ("Part No", PART),
            ("Revision", revision),
            ("Effective From", effective_from),
            ("Material", "AL6061"),
            ("Heat Treatment", "T6"),
            ("Characteristic ID", "DIM-001"),
            ("Characteristic Name", "Hole diameter"),
            ("Nominal (mm)", "10.00"),
            ("Tolerance +/- (mm)", tolerance),
        ]

        path = helper.create_pdf(
            f"{DRAWING}_Rev{revision}.pdf",
            "ENGINEERING DRAWING",
            fields,
            schematic=True,
        )

        drawings.append(
            drawing_parser.parse_drawing_pdf(path)
        )

    # 최초 메일: 소재/열처리성적서
    for prefix, certificate_type, title in (
        ("MAT", "MATERIAL", "MATERIAL CERTIFICATE"),
        ("HT", "HEAT_TREATMENT", "HEAT TREATMENT CERTIFICATE"),
    ):
        certificate_id = f"{prefix}-MAIL-HOLD-001-C"

        fields = [
            ("Certificate ID", certificate_id),
            ("Certificate Type", certificate_type),
            ("Part No", PART),
            ("PO No", PO),
            ("Lot No", NEW_LOT),
            ("Supplier ID", SUPPLIER),
            ("Material", "AL6061"),
            ("Heat Treatment", "T6"),
            ("Heat No", HEAT_NO),
            ("Drawing Revision", "C"),
        ]

        path = helper.create_pdf(
            f"{certificate_id}.pdf",
            title,
            fields,
        )

        certificate_parser.parse_certificate_pdf(path)

    # 보완메일: 누락됐던 검사성적서
    helper.PDF_DIR = supplemental_dir

    inspection_path = helper.create_pdf(
        f"{INSPECTION_ID}.pdf",
        "INSPECTION REPORT",
        [
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
        ],
    )

    inspection = inspection_parser.parse_inspection_pdf(
        inspection_path
    )

    if inspection["missing_fields"] or inspection["errors"]:
        raise ValueError(
            f"검사성적서 추출 오류: {inspection}"
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        with conn:
            helper.insert_or_check(
                conn, "parts",
                {
                    "part_no": PART,
                    "part_name": "Mail Hold Test Plate",
                    "drawing_no": DRAWING,
                },
                ["part_no"],
            )

            helper.insert_or_check(
                conn, "suppliers",
                {
                    "supplier_id": SUPPLIER,
                    "supplier_name": SUPPLIER_NAME,
                },
                ["supplier_id"],
            )

            helper.insert_or_check(
                conn, "purchase_orders",
                {
                    "po_no": PO,
                    "part_no": PART,
                    "supplier_id": SUPPLIER,
                    "supplier_name": SUPPLIER_NAME,
                    "order_date": "2026-09-01",
                },
                ["po_no"],
            )

            for lot, date, revision, tolerance, measured, doc in (
                (
                    OLD_LOT, "2026-09-18", "B",
                    0.10, 10.08, "INS-MAIL-HOLD-001-B",
                ),
                (
                    NEW_LOT, "2026-09-22", "C",
                    0.05, 10.02, INSPECTION_ID,
                ),
            ):
                helper.insert_or_check(
                    conn, "lot_samples",
                    {
                        "part_no": PART,
                        "po_no": PO,
                        "lot_no": lot,
                        "production_date": date,
                        "effectivity_date": EFFECTIVITY,
                        "revision": revision,
                        "document_id": doc,
                        "nominal_mm": 10.0,
                        "tolerance_mm": tolerance,
                        "measured_mm": measured,
                    },
                    ["lot_no"],
                )

            for drawing in drawings:
                helper.insert_or_check(
                    conn, "drawings",
                    {
                        "drawing_no": drawing["drawing_no"],
                        "part_no": drawing["part_no"],
                        "revision": drawing["revision"],
                        "effective_from": drawing["effective_from"],
                        "drawing_json": json.dumps(
                            drawing,
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                    },
                    ["drawing_no", "part_no", "revision"],
                )

    finally:
        conn.close()

    initial_email = (
        f"제목: [설계변경 검증] {DRAWING} Rev.B → Rev.C / {PO}\n\n"
        f"Part: {PART}\n"
        f"PO: {PO}\n"
        f"Supplier: {SUPPLIER}\n"
        f"Effectivity: {EFFECTIVITY} 생산분부터 C 적용\n"
        f"변경 전 Lot: {OLD_LOT}, 2026-09-18 생산\n"
        f"변경 후 Lot: {NEW_LOT}, 2026-09-22 생산\n\n"
        "도면 2개와 소재·열처리성적서를 첨부합니다.\n"
        "검사성적서는 후속 제출 예정입니다.\n"
    )

    supplemental_email = (
        "제목: [보완자료] <실제 Case ID로 교체> 검사성적서 제출\n\n"
        "Case ID: <최초 메일로 생성된 실제 Case ID로 교체>\n"
        f"Part: {PART}\n"
        f"PO: {PO}\n"
        f"Lot: {NEW_LOT}\n"
        f"Supplier: {SUPPLIER}\n\n"
        "검사성적서를 보완 제출합니다.\n"
        "기존 Case의 재검증을 요청합니다.\n"
    )

    (OUTPUT_DIR / "initial_email.txt").write_text(
        initial_email, encoding="utf-8"
    )
    (OUTPUT_DIR / "supplemental_email.txt").write_text(
        supplemental_email, encoding="utf-8"
    )

    print("최초 메일용 PDF 4개 생성 완료")
    print("보완메일용 검사성적서 1개 생성 완료")
    print("기존 Parser로 PDF 추출 확인 완료")
    print("DB 기준정보와 전후 Lot 저장 완료")
    print("Case와 수신 성적서는 미리 등록하지 않았습니다.")
    print(f"최초 첨부 폴더: {initial_dir}")
    print(f"보완 첨부 폴더: {supplemental_dir}")


if __name__ == "__main__":
    main()