import json
import shutil
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent

DOCUMENT_DIR = DATA_DIR / "documents"
DRAWING_DIR = DATA_DIR / "drawing_pdfs"
TEST_CASE_DIR = DATA_DIR / "test_cases"


def save_json(path, data):
    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def copy_file(source, destination_dir):
    destination_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        source,
        destination_dir / source.name,
    )


def create_case(
    case_id,
    part_no,
    po_no,
    lot_no,
    supplier_id,
    supplier_name,
    revision,
    initial_documents,
    supplemental_documents=None,
):
    case_dir = TEST_CASE_DIR / case_id

    initial_dir = (
        case_dir / "initial_attachments"
    )

    supplemental_dir = (
        case_dir / "supplemental_attachments"
    )

    initial_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    supplemental_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    case_data = {
        "case_id": case_id,
        "part_no": part_no,
        "po_no": po_no,
        "lot_no": lot_no,
        "supplier_id": supplier_id,
        "supplier_name": supplier_name,
        "drawing_revision": revision,
        "case_status": "OPEN",
    }

    save_json(
        case_dir / "case.json",
        case_data,
    )

    initial_email = {
        "sender": (
            f"quality@{supplier_id.lower()}.example.com"
        ),
        "subject": (
            f"{part_no} / {lot_no} 품질자료 제출"
        ),
        "body": (
            f"{po_no} 관련 {lot_no} 품질자료를 "
            "전달드립니다."
        ),
        "supplier_id": supplier_id,
        "part_no": part_no,
        "po_no": po_no,
        "lot_no": lot_no,
        "drawing_revision": revision,
        "attachment_files": initial_documents,
    }

    save_json(
        case_dir / "initial_email.json",
        initial_email,
    )

    for file_name in initial_documents:
        if file_name.startswith("DWG-"):
            source = DRAWING_DIR / file_name
        else:
            source = DOCUMENT_DIR / file_name

        copy_file(
            source,
            initial_dir,
        )

    if supplemental_documents:
        supplemental_email = {
            "sender": (
                f"quality@{supplier_id.lower()}.example.com"
            ),
            "subject": (
                f"RE: {part_no} / {lot_no} "
                "보완자료 제출"
            ),
            "body": (
                "요청하신 보완자료를 "
                "추가 제출드립니다."
            ),
            "supplier_id": supplier_id,
            "part_no": part_no,
            "po_no": po_no,
            "lot_no": lot_no,
            "attachment_files":
                supplemental_documents,
        }

        save_json(
            case_dir / "supplemental_email.json",
            supplemental_email,
        )

        for file_name in supplemental_documents:
            source = DOCUMENT_DIR / file_name

            copy_file(
                source,
                supplemental_dir,
            )


TEST_CASE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# CASE-001
create_case(
    case_id="CASE-001",
    part_no="P-001",
    po_no="PO-001",
    lot_no="LOT-002",
    supplier_id="SUP-001",
    supplier_name="경남정밀",
    revision="C",
    initial_documents=[
        "DWG-001_RevB.pdf",
        "DWG-001_RevC.pdf",
        "INS-002.pdf",
    ],
)


# CASE-002
create_case(
    case_id="CASE-002",
    part_no="P-001",
    po_no="PO-002",
    lot_no="LOT-005",
    supplier_id="SUP-002",
    supplier_name="진주에어로",
    revision="C",
    initial_documents=[
        "DWG-001_RevB.pdf",
        "DWG-001_RevC.pdf",
    ],
    supplemental_documents=[
        "INS-005.pdf",
    ],
)


# CASE-003
create_case(
    case_id="CASE-003",
    part_no="P-002",
    po_no="PO-003",
    lot_no="LOT-008",
    supplier_id="SUP-001",
    supplier_name="경남정밀",
    revision="C",
    initial_documents=[
        "DWG-002_RevB.pdf",
        "DWG-002_RevC.pdf",
        "INS-008.pdf",
    ],
)


print("테스트 Case 생성 완료")

for case_dir in sorted(TEST_CASE_DIR.iterdir()):
    if case_dir.is_dir():
        print(f"- {case_dir.name}")