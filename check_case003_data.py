import json
from copy import deepcopy
from pathlib import Path

from database.case_repository import get_case
from parser.drawing_parser import parse_drawing_pdf
from parser.pdf_parser import parse_inspection_pdf
from parser.quality_certificate_parser import parse_certificate_pdf
from tools.lot_trace import trace_impact
from tools.quality_verify import validate_quality


ROOT = Path(__file__).resolve().parent
checks = []


def check(name, actual, expected):
    passed = actual == expected

    checks.append({
        "name": name,
        "passed": passed,
        "actual": actual,
        "expected": expected,
    })

    print(f"{'PASS' if passed else 'FAIL'} | {name}")

    if not passed:
        print(json.dumps(
            {"actual": actual, "expected": expected},
            ensure_ascii=False,
            indent=2,
        ))


def main():
    data = get_case("CASE-003")

    if data is None:
        raise RuntimeError("CASE-003을 찾을 수 없습니다.")

    case = data["case"]
    lot = data["lot"]

    check("대상 Lot", case["lot_no"], "LOT-008")
    check("Case와 Lot의 부품번호", lot["part_no"], case["part_no"])
    check("Case와 Lot의 발주번호", lot["po_no"], case["po_no"])

    parsers = {
        "DRAWING": parse_drawing_pdf,
        "INSPECTION_REPORT": parse_inspection_pdf,
        "MATERIAL_CERTIFICATE": parse_certificate_pdf,
        "HEAT_TREATMENT_CERTIFICATE": parse_certificate_pdf,
    }

    fresh = deepcopy(data)
    parsed_count = 0

    for index, document in enumerate(data["documents"]):
        name = document["file_name"]
        kind = document["document_type"]

        try:
            parsed = parsers[kind](document["file_path"])
            stored = document.get("structured_data")

            check(f"{name}: PDF 재분석 결과와 DB 일치", parsed, stored)
            check(f"{name}: 파싱 오류", parsed.get("errors", []), [])
            check(f"{name}: 누락 항목", parsed.get("missing_fields", []), [])
            check(f"{name}: 부품번호", parsed.get("part_no"), case["part_no"])

            if kind != "DRAWING":
                for key in ("lot_no", "po_no"):
                    check(f"{name}: {key}", parsed.get(key), case[key])

            if kind == "INSPECTION_REPORT":
                for key in (
                    "production_date", "revision", "nominal_mm",
                    "tolerance_mm", "measured_mm",
                ):
                    check(
                        f"{name}: Lot 테이블의 {key}와 일치",
                        parsed.get(key),
                        lot[key],
                    )

            if (
                kind == "DRAWING"
                and parsed["revision"] == case["drawing_revision"]
            ):
                check(
                    f"{name}: 도면과 Lot의 적용일 일치",
                    parsed["effective_from"],
                    lot["effectivity_date"],
                )
                characteristic = parsed["characteristics"][0]
                check("새 도면 기준 치수", characteristic["nominal_mm"], 20.0)
                check("새 도면 공차", characteristic["tolerance_mm"], 0.1)

            fresh["documents"][index]["structured_data"] = parsed
            parsed_count += 1

        except Exception as error:
            check(
                f"{name}: PDF 처리 오류",
                f"{type(error).__name__}: {error}",
                None,
            )

    check("정상적으로 읽은 PDF 개수", parsed_count, 5)

    for label, source in (("DB 자료", data), ("다시 읽은 PDF 자료", fresh)):
        if label == "다시 읽은 PDF 자료" and parsed_count != len(data["documents"]):
            print("미실행 | PDF를 모두 읽지 못해 PDF 기반 판정을 건너뜁니다.")
            continue

        impact = trace_impact(source)
        targets = impact["result"]["affected_lots"]

        check(
            f"{label}: 변경 적용 대상",
            impact["result"]["impact_status"],
            "IN_EFFECTIVITY_SCOPE",
        )
        check(
            f"{label}: 영향 Lot 목록",
            [item["lot_no"] for item in targets],
            ["LOT-008"],
        )

        result = validate_quality(source, affected_lots=targets)
        verdicts = [
            (item["decision"], item["issue_code"])
            for item in result["result"]["lot_results"]
        ]

        check(
            f"{label}: 공차 초과 불합격 판정",
            verdicts,
            [("REJECT", "DIMENSION_OUT_OF_TOLERANCE")],
        )

    print("\n적용일 경계 검사: 복사한 메모리 자료만 사용합니다.")

    boundaries = (
        ("2026-09-19", "BEFORE_EFFECTIVITY"),
        ("2026-09-20", "IN_EFFECTIVITY_SCOPE"),
        ("2026-09-21", "IN_EFFECTIVITY_SCOPE"),
    )

    for day, expected in boundaries:
        sample = deepcopy(data)
        sample["lot"]["production_date"] = day
        sample["lot"]["effectivity_date"] = "2026-09-20"

        impact = trace_impact(sample)
        targets = impact["result"]["affected_lots"]

        check(
            f"생산일 {day}: 적용 범위",
            impact["result"]["impact_status"],
            expected,
        )
        check(
            f"생산일 {day}: 영향 Lot 목록",
            [item["lot_no"] for item in targets],
            [] if expected == "BEFORE_EFFECTIVITY" else ["LOT-008"],
        )

        if expected == "BEFORE_EFFECTIVITY":
            result = validate_quality(sample, affected_lots=targets)
            check(
                "적용일 이전 Lot은 품질판정 대상에서 제외",
                result["result"]["lot_results"],
                [],
            )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        check("실행 오류", f"{type(error).__name__}: {error}", None)

    report = ROOT / "case003_data_check_result.json"
    report.write_text(
        json.dumps(checks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    failed = sum(not item["passed"] for item in checks)

    print(
        f"\n총 {len(checks)}개 검사: "
        f"PASS {len(checks) - failed}, FAIL {failed}"
    )
    print(f"결과 파일: {report}")

    raise SystemExit(1 if failed else 0)