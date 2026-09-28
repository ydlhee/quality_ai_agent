import json
import shutil
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent

DOCUMENT_DIR = DATA_DIR / "documents"
DRAWING_DIR = DATA_DIR / "drawing_pdfs"
QUALITY_CERT_DIR = DATA_DIR / "quality_certificates"
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
    if not source.exists():
        raise FileNotFoundError(
            f"첨부파일을 찾을 수 없습니다: {source}"
        )

    destination_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        source,
        destination_dir / source.name,
    )


def get_source_path(file_name):
    """
    파일명에 따라 원본 파일 위치를 결정한다.
    """

    if file_name.startswith("DWG-"):
        return DRAWING_DIR / file_name

    if (
        file_name.startswith("MAT-")
        or file_name.startswith("HT-")
    ):
        return QUALITY_CERT_DIR / file_name

    return DOCUMENT_DIR / file_name


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

    # 이전 실행에서 남은 첨부파일 제거
    if initial_dir.exists():
        shutil.rmtree(initial_dir)

    if supplemental_dir.exists():
        shutil.rmtree(supplemental_dir)

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

    # 최초 첨부자료 복사
    for file_name in initial_documents:
        source = get_source_path(file_name)

        copy_file(
            source,
            initial_dir,
        )

    # 보완자료가 있는 Case
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
            source = get_source_path(file_name)

            copy_file(
                source,
                supplemental_dir,
            )

    else:
        # 이전 실행에서 보완메일이 남아 있는 경우 제거
        supplemental_email_path = (
            case_dir / "supplemental_email.json"
        )

        if supplemental_email_path.exists():
            supplemental_email_path.unlink()


TEST_CASE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# CASE-001
# 정상 자료 보유 사례
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
        "MAT-002.pdf",
        "HT-002.pdf",
    ],
)


# CASE-002
# 검사성적서 누락 사례
# 소재성적서와 열처리성적서는 최초부터 존재
# INS-005만 보완자료로 나중에 추가
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
        "MAT-005.pdf",
        "HT-005.pdf",
    ],
    supplemental_documents=[
        "INS-005.pdf",
    ],
)


# CASE-003
# 요구조건 불일치 사례
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
        "MAT-008.pdf",
        "HT-008.pdf",
    ],
)


print("테스트 Case 생성 완료")

for case_dir in sorted(TEST_CASE_DIR.iterdir()):
    if case_dir.is_dir():
        print(f"- {case_dir.name}")