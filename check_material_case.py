import json
import shutil
import sqlite3
import tempfile
from copy import deepcopy
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

import database.case_repository as repository
from parser.pdf_parser import FIELD_MAP as INS_FIELDS
from parser.pdf_parser import parse_inspection_pdf
from parser.quality_certificate_parser import FIELD_MAP as CERT_FIELDS
from parser.quality_certificate_parser import parse_certificate_pdf
from tools.lot_trace import trace_impact
from tools.quality_verify import validate_quality


ROOT = Path(__file__).resolve().parent
CASE_ID = "CASE-003"


def write_pdf(path, title, fields, values):
    pdf = canvas.Canvas(str(path), pagesize=A4)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(45, 795, title)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(
        45, 770,
        "SYNTHETIC TEST ONLY - NOT FOR MANUFACTURING",
    )
    pdf.setFont("Helvetica", 11)

    y = 735
    for label, key in fields.items():
        pdf.drawString(45, y, f"{label}: {values[key]}")
        y -= 30

    pdf.save()


def update_document(db_path, table, parsed):
    # 별도 테스트 DB에서만 호출한다.
    if table not in {
        "inspection_documents",
        "quality_certificates",
    }:
        raise ValueError(table)

    with sqlite3.connect(db_path) as conn:
        columns = {
            row[1]
            for row in conn.execute(
                f'PRAGMA table_info("{table}")'
            )
        }

        values = {
            key: value
            for key, value in parsed.items()
            if key in columns
            and key not in {"source_file", "lot_no"}
            and not isinstance(value, (dict, list))
        }
        values["extracted_json"] = json.dumps(
            parsed, ensure_ascii=False
        )

        assignments = ", ".join(
            f'"{key}" = ?' for key in values
        )

        cursor = conn.execute(
            f'UPDATE "{table}" SET {assignments} '
            "WHERE source_file = ? AND lot_no = ?",
            [
                *values.values(),
                parsed["source_file"],
                parsed["lot_no"],
            ],
        )

        if cursor.rowcount != 1:
            raise RuntimeError(
                f"{table}: 수정 대상이 1행이어야 하는데 "
                f"{cursor.rowcount}행입니다."
            )


def main():
    original_db = repository.DB_PATH
    original_cases = repository.TEST_CASE_DIR

    original = repository.get_case(CASE_ID)
    if original is None:
        raise RuntimeError("CASE-003을 찾을 수 없습니다.")

    if original["lot"]["revision"] != "C":
        raise RuntimeError(
            "CASE-003 Lot Revision이 C인지 확인하세요."
        )

    output_root = ROOT / "data" / "material_validation_runs"
    output_root.mkdir(parents=True, exist_ok=True)

    # 실행할 때마다 새로운 폴더를 만든다.
    run_dir = Path(
        tempfile.mkdtemp(prefix="run_", dir=output_root)
    )
    test_db = run_dir / "test.db"
    test_cases = run_dir / "test_cases"

    shutil.copytree(
        Path(original_cases) / CASE_ID,
        test_cases / CASE_ID,
    )

    # 원본 DB는 읽기 전용으로 열어 복사한다.
    source_uri = (
        Path(original_db).resolve().as_uri() + "?mode=ro"
    )
    with sqlite3.connect(source_uri, uri=True) as source:
        with sqlite3.connect(test_db) as target:
            source.backup(target)

    report = {
        "test_id": "MATERIAL-REJECT-001",
        "source_case": CASE_ID,
        "isolated_db": str(test_db),
        "checks": [],
        "phases": {},
    }

    def check(name, actual, expected):
        passed = actual == expected
        report["checks"].append({
            "name": name,
            "passed": passed,
            "actual": actual,
            "expected": expected,
        })
        print(f"{'PASS' if passed else 'FAIL'} | {name}")

        if not passed:
            raise AssertionError(
                f"{name}: 실제={actual!r}, 예상={expected!r}"
            )

    def get_document(data, kind):
        matches = [
            document
            for document in data["documents"]
            if document["document_type"] == kind
        ]
        if len(matches) != 1:
            raise RuntimeError(
                f"{kind}: 문서가 정확히 1개 필요합니다. "
                f"현재 {len(matches)}개"
            )
        return matches[0]

    def validate_phase(name, expected):
        data = repository.get_case(CASE_ID)

        impact = trace_impact(data, case_id=CASE_ID)
        lots = [
            lot["lot_no"]
            for lot in impact["result"]["affected_lots"]
        ]

        quality = validate_quality(
            data,
            affected_lots=lots,
            case_id=CASE_ID,
        )

        report["phases"][name] = {
            "input": data,
            "trace_impact": impact,
            "validate_quality": quality,
            "expected": expected,
        }

        check(
            name + " 영향범위",
            impact["result"]["impact_status"],
            "IN_EFFECTIVITY_SCOPE",
        )
        check(
            name + " 대상 Lot",
            lots,
            [data["lot"]["lot_no"]],
        )

        results = quality["result"]["lot_results"]
        check(
            name + " 품질판정",
            [
                [result["decision"], result["issue_code"]]
                for result in results
            ],
            [expected],
        )

    try:
        # 이 실행 중에만 조회 대상을 복사본으로 전환한다.
        repository.DB_PATH = test_db
        repository.TEST_CASE_DIR = test_cases

        data = repository.get_case(CASE_ID)
        inspection = get_document(
            data, "INSPECTION_REPORT"
        )
        material = get_document(
            data, "MATERIAL_CERTIFICATE"
        )

        new_drawing = next(
            document["structured_data"]
            for document in data["documents"]
            if document["document_type"] == "DRAWING"
            and document["structured_data"]["revision"] == "C"
        )

        check(
            "도면 요구 재질",
            new_drawing["material"],
            "Ti-6Al-4V",
        )
        check(
            "정상 대조군 소재 재질",
            material["structured_data"]["material"],
            "Ti-6Al-4V",
        )

        # 1. 복사본의 기존 공차 초과를 정상 치수로 변경한다.
        values = deepcopy(inspection["structured_data"])
        values["measured_mm"] = 20.05

        inspection_path = Path(inspection["file_path"])
        write_pdf(
            inspection_path,
            "INSPECTION REPORT",
            INS_FIELDS,
            values,
        )
        parsed = parse_inspection_pdf(inspection_path)

        check("검사성적서 파싱 오류", parsed["errors"], [])
        check(
            "검사성적서 누락 항목",
            parsed["missing_fields"],
            [],
        )

        update_document(
            test_db, "inspection_documents", parsed
        )

        with sqlite3.connect(test_db) as conn:
            cursor = conn.execute(
                "UPDATE lot_samples SET measured_mm = ? "
                "WHERE lot_no = ?",
                (20.05, data["lot"]["lot_no"]),
            )
            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Lot 수정 대상이 정확히 1행이어야 합니다."
                )

        loaded = repository.get_case(CASE_ID)
        check(
            "검사성적서 PDF와 DB 일치",
            get_document(
                loaded, "INSPECTION_REPORT"
            )["structured_data"],
            parsed,
        )
        check(
            "Lot 테이블 측정값",
            loaded["lot"]["measured_mm"],
            20.05,
        )

        validate_phase(
            "baseline",
            ["PASS", "NO_ISSUE"],
        )

        # 2. 정상 소재성적서를 보관한 뒤 재질만 바꾼다.
        material_path = Path(material["file_path"])
        shutil.copy2(
            material_path,
            run_dir / "baseline_material.pdf",
        )

        values = deepcopy(material["structured_data"])
        values["material"] = "AL6061"

        write_pdf(
            material_path,
            "MATERIAL CERTIFICATE",
            CERT_FIELDS,
            values,
        )
        parsed = parse_certificate_pdf(material_path)

        update_document(
            test_db, "quality_certificates", parsed
        )

        loaded = repository.get_case(CASE_ID)
        check(
            "소재성적서 PDF와 DB 일치",
            get_document(
                loaded, "MATERIAL_CERTIFICATE"
            )["structured_data"],
            parsed,
        )
        check(
            "불일치 재질",
            parsed["material"],
            "AL6061",
        )

        validate_phase(
            "material_mismatch",
            ["REJECT", "MATERIAL_MISMATCH"],
        )
        report["status"] = "PASS"

    except Exception as error:
        report["status"] = "FAIL"
        report["error"] = (
            f"{type(error).__name__}: {error}"
        )
        print(report["error"])

    finally:
        repository.DB_PATH = original_db
        repository.TEST_CASE_DIR = original_cases

        result_path = run_dir / "result.json"
        result_path.write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        print("\nTEST RESULT:", report["status"])
        print("결과 파일:", result_path)
        print("원본 DB와 PDF는 변경하지 않았습니다.")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())