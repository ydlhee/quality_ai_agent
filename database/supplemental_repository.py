import hashlib
import json
import re
import shutil
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "sample_lots.db"

SUPPORTED_TYPES = {
    "INSPECTION_REPORT",
    "MATERIAL_CERTIFICATE",
    "HEAT_TREATMENT_CERTIFICATE",
}


def require_text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: 비어 있지 않은 문자열이 필요합니다.")
    return value


def create_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inspection_documents (
            source_file TEXT PRIMARY KEY,
            document_id TEXT,
            lot_no TEXT,
            part_no TEXT,
            extracted_json TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS quality_certificates (
            certificate_id TEXT PRIMARY KEY,
            certificate_type TEXT NOT NULL,
            part_no TEXT NOT NULL,
            po_no TEXT NOT NULL,
            lot_no TEXT NOT NULL,
            supplier_id TEXT NOT NULL,
            material TEXT NOT NULL,
            heat_treatment TEXT NOT NULL,
            heat_no TEXT NOT NULL,
            source_file TEXT NOT NULL,
            extracted_json TEXT NOT NULL
        )
    """)

    # 같은 Gmail 첨부를 반복 처리하지 않기 위한 기록
    conn.execute("""
        CREATE TABLE IF NOT EXISTS supplemental_receipts (
            mailbox_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            attachment_id TEXT NOT NULL,
            case_id TEXT NOT NULL,
            original_name TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            document_type TEXT NOT NULL,
            PRIMARY KEY (
                mailbox_id, message_id, attachment_id
            )
        )
    """)

    # 같은 PDF를 다른 메일로 다시 보낸 경우도 중복 방지
    conn.execute("""
        CREATE TABLE IF NOT EXISTS supplemental_contents (
            case_id TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            document_type TEXT NOT NULL,
            PRIMARY KEY (case_id, sha256)
        )
    """)


def insert_identical(conn, table, key, record):
    existing = conn.execute(
        f"SELECT * FROM {table} WHERE {key} = ?",
        (record[key],),
    ).fetchone()

    if existing is not None:
        if any(existing[k] != v for k, v in record.items()):
            raise ValueError(
                f"{table}: 기존 {key}={record[key]}의 내용과 다릅니다. "
                "덮어쓰지 않았습니다. 정정본은 새 문서 ID를 사용하세요."
            )
        return

    columns = ", ".join(record)
    placeholders = ", ".join("?" for _ in record)

    conn.execute(
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
        tuple(record.values()),
    )


def register_supplemental(
    case_id,
    message_id,
    attachments,
    *,
    mailbox_id="default",
    db_path=None,
    project_root=None,
):
    """
    기존 Case에 Gmail 보완문서를 저장한다.

    attachments 예시:
    [{
        "attachment_id": "Gmail 첨부 ID",
        "file_name": "INS-001.pdf",
        "file_path": "다운로드한 PDF 경로",
        "document_type": "INSPECTION_REPORT",
        "parsed_data": 기존_Parser의_반환값,
    }]

    Case 상태 변경이나 Agent 실행은 하지 않는다.
    """
    for name, value in (
        ("case_id", case_id),
        ("message_id", message_id),
        ("mailbox_id", mailbox_id),
    ):
        require_text(value, name)

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", case_id):
        raise ValueError("Case ID에 경로로 사용할 수 없는 문자가 있습니다.")

    if not isinstance(attachments, list) or not attachments:
        raise ValueError("attachments는 비어 있지 않은 목록이어야 합니다.")

    root = Path(project_root).resolve() if project_root else ROOT
    db = Path(db_path).resolve() if db_path else DB_PATH

    if not db.is_file():
        raise FileNotFoundError(f"기존 프로젝트 DB가 없습니다: {db}")

    destination = (
        root
        / "data"
        / "test_cases"
        / case_id
        / "supplemental_attachments"
    ).resolve()

    if not destination.is_relative_to(root):
        raise ValueError("첨부 저장 경로가 프로젝트 밖입니다.")

    prepared = []

    for item in attachments:
        source = Path(item["file_path"]).resolve()

        if not source.is_file():
            raise FileNotFoundError(source)

        file_name = item.get("file_name", source.name)
        require_text(file_name, "file_name")

        if (
            "/" in file_name
            or "\\" in file_name
            or not file_name.lower().endswith(".pdf")
        ):
            raise ValueError("file_name에는 PDF 파일명만 넣어 주세요.")

        document_type = item["document_type"]

        if document_type not in SUPPORTED_TYPES:
            raise ValueError(
                f"지원하지 않는 문서 유형: {document_type}"
            )

        if not isinstance(item.get("parsed_data"), dict):
            raise ValueError("parsed_data는 dict 형식이어야 합니다.")

        # 전달받은 원본 dict는 수정하지 않는다.
        payload = json.loads(
            json.dumps(
                item["parsed_data"],
                ensure_ascii=False,
                allow_nan=False,
            )
        )

        digest = hashlib.sha256(source.read_bytes()).hexdigest()

        attachment_id = (
            item.get("attachment_id")
            or f"{file_name}:{digest}"
        )
        require_text(attachment_id, "attachment_id")

        identity = hashlib.sha256(
            f"{case_id}:{digest}".encode()
        ).hexdigest()

        prefix = {
            "INSPECTION_REPORT": "INS",
            "MATERIAL_CERTIFICATE": "MAT",
            "HEAT_TREATMENT_CERTIFICATE": "HT",
        }[document_type]

        stored_name = f"{prefix}-SUP-{identity}.pdf"

        prepared.append((
            source,
            file_name,
            document_type,
            payload,
            digest,
            attachment_id,
            stored_name,
        ))

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    created_files = []
    results = []
    committed = False

    try:
        conn.execute("BEGIN IMMEDIATE")

        case = conn.execute(
            "SELECT * FROM cases WHERE case_id = ?",
            (case_id,),
        ).fetchone()

        if case is None:
            raise ValueError(f"기존 Case가 없습니다: {case_id}")

        conn.execute("""
            SELECT case_id, file_name, document_stage
            FROM case_documents
            LIMIT 0
        """)

        create_tables(conn)
        destination.mkdir(parents=True, exist_ok=True)

        for (
            source,
            file_name,
            document_type,
            payload,
            digest,
            attachment_id,
            stored_name,
        ) in prepared:
            required_keys = ["part_no", "po_no", "lot_no"]

            if document_type != "INSPECTION_REPORT":
                required_keys.append("supplier_id")

            for key in required_keys:
                require_text(payload.get(key), key)

                if payload[key] != case[key]:
                    raise ValueError(
                        f"{file_name}: {key}가 {case_id}와 다릅니다."
                    )

            if (
                payload.get("supplier_id")
                and payload["supplier_id"] != case["supplier_id"]
            ):
                raise ValueError(
                    f"{file_name}: Supplier가 Case와 다릅니다."
                )

            if document_type == "INSPECTION_REPORT":
                require_text(
                    payload.get("document_id"), "document_id"
                )
            else:
                for key in (
                    "certificate_id",
                    "certificate_type",
                    "material",
                    "heat_treatment",
                    "heat_no",
                ):
                    require_text(payload.get(key), key)

                allowed_types = {
                    "MATERIAL_CERTIFICATE": {
                        "MATERIAL",
                        "MATERIAL_CERTIFICATE",
                    },
                    "HEAT_TREATMENT_CERTIFICATE": {
                        "HEAT_TREATMENT",
                        "HEAT_TREATMENT_CERTIFICATE",
                    },
                }

                if (
                    payload["certificate_type"]
                    not in allowed_types[document_type]
                ):
                    raise ValueError(
                        f"{file_name}: 성적서 유형이 일치하지 않습니다."
                    )

            receipt = conn.execute("""
                SELECT *
                FROM supplemental_receipts
                WHERE mailbox_id = ?
                  AND message_id = ?
                  AND attachment_id = ?
            """, (
                mailbox_id,
                message_id,
                attachment_id,
            )).fetchone()

            if receipt and (
                receipt["case_id"] != case_id
                or receipt["sha256"] != digest
                or receipt["document_type"] != document_type
            ):
                raise ValueError(
                    "같은 Gmail 첨부 ID의 Case·내용·유형이 달라졌습니다."
                )

            prior = conn.execute("""
                SELECT *
                FROM supplemental_contents
                WHERE case_id = ? AND sha256 = ?
            """, (case_id, digest)).fetchone()

            if prior:
                if prior["document_type"] != document_type:
                    raise ValueError(
                        "같은 PDF가 다른 문서 유형으로 전달됐습니다."
                    )
                stored_name = prior["stored_name"]

            target = destination / stored_name

            if target.exists():
                existing_hash = hashlib.sha256(
                    target.read_bytes()
                ).hexdigest()

                if existing_hash != digest:
                    raise ValueError(
                        f"기존 저장 파일의 내용이 다릅니다: {target}"
                    )
            else:
                with target.open("xb") as output:
                    created_files.append(target)
                    with source.open("rb") as input_file:
                        shutil.copyfileobj(input_file, output)

                if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                    raise ValueError("복사 중 원본 파일이 변경됐습니다.")

            if not prior:
                payload["source_file"] = stored_name
                payload["original_source_file"] = file_name

                encoded = json.dumps(
                    payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    allow_nan=False,
                )

                if document_type == "INSPECTION_REPORT":
                    insert_identical(
                        conn,
                        "inspection_documents",
                        "source_file",
                        {
                            "source_file": stored_name,
                            "document_id": payload["document_id"],
                            "lot_no": payload["lot_no"],
                            "part_no": payload["part_no"],
                            "extracted_json": encoded,
                        },
                    )
                else:
                    record = {
                        key: payload[key]
                        for key in (
                            "certificate_id",
                            "certificate_type",
                            "part_no",
                            "po_no",
                            "lot_no",
                            "supplier_id",
                            "material",
                            "heat_treatment",
                            "heat_no",
                        )
                    }

                    record["source_file"] = stored_name
                    record["extracted_json"] = encoded

                    insert_identical(
                        conn,
                        "quality_certificates",
                        "certificate_id",
                        record,
                    )

                conn.execute("""
                    INSERT INTO case_documents (
                        case_id,
                        file_name,
                        document_type,
                        document_stage,
                        source_email
                    )
                    VALUES (?, ?, ?, 'SUPPLEMENTAL', ?)
                """, (
                    case_id,
                    stored_name,
                    document_type,
                    f"gmail:{mailbox_id}:{message_id}",
                ))

                conn.execute("""
                    INSERT INTO supplemental_contents (
                        case_id, sha256, stored_name, document_type
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    case_id,
                    digest,
                    stored_name,
                    document_type,
                ))

            if not receipt:
                conn.execute("""
                    INSERT INTO supplemental_receipts (
                        mailbox_id,
                        message_id,
                        attachment_id,
                        case_id,
                        original_name,
                        sha256,
                        stored_name,
                        document_type
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    mailbox_id,
                    message_id,
                    attachment_id,
                    case_id,
                    file_name,
                    digest,
                    stored_name,
                    document_type,
                ))

            results.append({
                "file_name": file_name,
                "stored_name": stored_name,
                "file_path": str(target),
                "status": "skipped" if prior else "added",
            })

        conn.commit()
        committed = True

    except Exception:
        conn.rollback()
        raise

    finally:
        if not committed:
            for path in created_files:
                path.unlink(missing_ok=True)
        conn.close()

    return {
        "case_id": case_id,
        "message_id": message_id,
        "added_count": sum(
            item["status"] == "added" for item in results
        ),
        "skipped_count": sum(
            item["status"] == "skipped" for item in results
        ),
        "documents": results,
    }