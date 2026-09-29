import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from supplemental_repository import register_supplemental


class SupplementalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "test.db"

        with closing(sqlite3.connect(self.db)) as conn:
            conn.executescript("""
                CREATE TABLE cases (
                    case_id TEXT PRIMARY KEY,
                    part_no TEXT,
                    po_no TEXT,
                    lot_no TEXT,
                    supplier_id TEXT,
                    supplier_name TEXT,
                    drawing_revision TEXT,
                    case_status TEXT
                );

                INSERT INTO cases VALUES (
                    'LIVE-001', 'P-1', 'PO-1', 'LOT-1',
                    'SUP-1', 'Supplier', 'C', 'HOLD'
                );

                INSERT INTO cases VALUES (
                    'CASE-001', 'P-OLD', 'PO-OLD', 'LOT-OLD',
                    'SUP-OLD', 'Old Supplier', 'B', 'OPEN'
                );

                CREATE TABLE case_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT,
                    file_name TEXT,
                    document_type TEXT,
                    document_stage TEXT,
                    source_email TEXT,
                    UNIQUE(case_id, file_name, document_stage)
                );

                INSERT INTO case_documents (
                    case_id,
                    file_name,
                    document_type,
                    document_stage,
                    source_email
                )
                VALUES (
                    'CASE-001',
                    'OLD.pdf',
                    'DRAWING',
                    'INITIAL',
                    'initial_email.json'
                );
            """)
            conn.commit()

        self.pdf = self.root / "INS-1.pdf"

        # 저장 기능 확인용 파일.
        # 실제 PDF 파싱은 자료 생성 코드에서 별도로 확인한다.
        self.pdf.write_bytes(b"inspection fixture bytes")

        self.item = {
            "file_path": str(self.pdf),
            "attachment_id": "attachment-1",
            "document_type": "INSPECTION_REPORT",
            "parsed_data": {
                "document_id": "INS-1",
                "part_no": "P-1",
                "po_no": "PO-1",
                "lot_no": "LOT-1",
                "measured_mm": 10.02,
                "missing_fields": [],
                "errors": [],
                "evidence": {
                    "measured_mm": {
                        "page": 1,
                        "text": "Measured (mm): 10.02",
                    }
                },
            },
        }

    def tearDown(self):
        self.temp.cleanup()

    def save(self, items=None, message_id="message-1"):
        return register_supplemental(
            case_id="LIVE-001",
            message_id=message_id,
            mailbox_id="test-account",
            attachments=[self.item] if items is None else items,
            db_path=self.db,
            project_root=self.root,
        )

    def query(self, sql):
        with closing(sqlite3.connect(self.db)) as conn:
            return conn.execute(sql).fetchall()

    def test_save_and_duplicates(self):
        """저장, 중복 방지, 기존 Case 보존 확인."""
        result = self.save()

        self.assertEqual(result["added_count"], 1)

        # 같은 메일을 다시 처리하는 경우
        repeated = self.save()
        self.assertEqual(repeated["added_count"], 0)
        self.assertEqual(repeated["skipped_count"], 1)

        # 다른 메일로 같은 PDF를 다시 보내는 경우
        forwarded = self.save(message_id="message-2")
        self.assertEqual(forwarded["added_count"], 0)
        self.assertEqual(forwarded["skipped_count"], 1)

        self.assertEqual(
            self.query(
                "SELECT COUNT(*) FROM inspection_documents"
            ),
            [(1,)],
        )

        self.assertEqual(
            self.query(
                "SELECT COUNT(*) FROM supplemental_receipts"
            ),
            [(2,)],
        )

        document = result["documents"][0]
        self.assertTrue(
            Path(document["file_path"]).is_file()
        )

        payload = json.loads(
            self.query(
                "SELECT extracted_json FROM inspection_documents"
            )[0][0]
        )

        self.assertEqual(
            payload["source_file"],
            document["stored_name"],
        )
        self.assertEqual(
            payload["original_source_file"],
            "INS-1.pdf",
        )
        self.assertEqual(
            payload["evidence"],
            self.item["parsed_data"]["evidence"],
        )

        # 보완자료 저장만으로 HOLD를 PASS로 바꾸지 않는다.
        self.assertEqual(
            self.query(
                "SELECT case_status FROM cases "
                "WHERE case_id = 'LIVE-001'"
            ),
            [("HOLD",)],
        )

        # 기존 Case의 문서를 유지한다.
        self.assertEqual(
            self.query(
                "SELECT file_name FROM case_documents "
                "WHERE case_id = 'CASE-001'"
            ),
            [("OLD.pdf",)],
        )

        self.assertEqual(
            self.query(
                "SELECT document_stage FROM case_documents "
                "WHERE case_id = 'LIVE-001'"
            ),
            [("SUPPLEMENTAL",)],
        )

    def test_wrong_lot_rejected(self):
        """다른 Lot의 문서는 저장하지 않는다."""
        self.item["parsed_data"]["lot_no"] = "OTHER-LOT"

        with self.assertRaises(ValueError):
            self.save()

        self.assertEqual(
            self.query(
                "SELECT COUNT(*) FROM case_documents"
            ),
            [(1,)],
        )

    def test_batch_rollback(self):
        """두 번째 첨부에 오류가 있으면 첫 번째 저장도 취소한다."""
        invalid = {
            **self.item,
            "attachment_id": "attachment-2",
            "parsed_data": {
                **self.item["parsed_data"],
                "part_no": "WRONG-PART",
            },
        }

        with self.assertRaises(ValueError):
            self.save([self.item, invalid])

        self.assertEqual(
            self.query(
                "SELECT COUNT(*) FROM case_documents"
            ),
            [(1,)],
        )

        self.assertFalse(
            list((self.root / "data").rglob("*.pdf"))
        )

    def test_changed_attachment_rejected(self):
        """같은 메일·첨부 ID로 다른 내용이 전달되면 중단한다."""
        self.save()

        self.pdf.write_bytes(b"different bytes")

        with self.assertRaises(ValueError):
            self.save()

        self.assertEqual(
            self.query(
                "SELECT COUNT(*) FROM inspection_documents"
            ),
            [(1,)],
        )

    def test_material_and_heat_certificates(self):
        """소재·열처리 저장과 기존 증명서 ID 충돌을 확인한다."""
        document_types = (
            "MATERIAL_CERTIFICATE",
            "HEAT_TREATMENT_CERTIFICATE",
        )

        for index, kind in enumerate(document_types):
            path = self.root / f"CERT-{index}.pdf"
            path.write_bytes(
                f"certificate-{index}".encode()
            )

            item = {
                "file_path": str(path),
                "attachment_id": f"cert-{index}",
                "document_type": kind,
                "parsed_data": {
                    "certificate_id": f"CERT-{index}",
                    "certificate_type": kind,
                    "part_no": "P-1",
                    "po_no": "PO-1",
                    "lot_no": "LOT-1",
                    "supplier_id": "SUP-1",
                    "material": "AL6061",
                    "heat_treatment": "T6",
                    "heat_no": "HEAT-1",
                },
            }

            result = self.save(
                [item],
                message_id=f"cert-message-{index}",
            )
            self.assertEqual(result["added_count"], 1)

            # 같은 certificate_id의 다른 파일을 덮어쓰지 않는다.
            if index == 0:
                path.write_bytes(b"changed certificate")

                with self.assertRaises(ValueError):
                    self.save(
                        [item],
                        message_id="changed-cert",
                    )

        self.assertEqual(
            self.query(
                "SELECT COUNT(*) FROM quality_certificates"
            ),
            [(2,)],
        )


if __name__ == "__main__":
    unittest.main()