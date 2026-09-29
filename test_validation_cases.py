"""기존 VAL-001~009 자료를 현재 Case Tool API로 실행한다.

원본 자료, DB, Tool은 수정하지 않는다.
누락된 날짜나 성적서를 임의로 만들지 않는다.
판정과 판정 원인이 모두 예상과 일치해야 테스트 성공이다.
"""

import csv
import json
import math
import sys
from pathlib import Path


# 이 파일은 quality_ai_agent 프로젝트 최상위에 둔다.
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from tools.drawing_compare import analyze_design_change
from tools.verification_plan import create_validation_plan
from tools.lot_trace import trace_impact
from tools.quality_verify import validate_quality
from tools.followup import handle_followup


# 기존 테스트 자료가 확인하려는 원인.
# 다른 이유로 HOLD/REJECT가 나온 경우 성공으로 세지 않는다.
EXPECTED_ISSUES = {
    "VAL-001": "NO_ISSUE",
    "VAL-002": "MEASUREMENT_MISSING",
    "VAL-003": "DIMENSION_OUT_OF_TOLERANCE",
    "VAL-004": "REVISION_MISMATCH",
    "VAL-005": "MATERIAL_MISMATCH",
    "VAL-006": "HEAT_TREATMENT_MISMATCH",
    "VAL-007": "REQUIRED_DOCUMENT_MISSING",
    "VAL-008": "HEAT_NO_MISMATCH",
    "VAL-009": "NO_ISSUE",
}


def load_json(path):
    with path.open(encoding="utf-8-sig") as stream:
        return json.load(stream)


def load_csv(path):
    with path.open(
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        return list(csv.DictReader(stream))


def number(value):
    """CSV의 빈 측정값은 None, 숫자는 float으로 변환한다."""
    if value is None or str(value).strip() == "":
        return None

    result = float(value)

    if not math.isfinite(result):
        raise ValueError(f"유효하지 않은 수치: {value}")

    return result


def document(kind, name, data):
    """현재 Tool이 사용하는 문서 구조를 만든다."""
    return {
        "document_type": kind,
        "file_name": name,
        "document_stage": "INITIAL",
        "structured_data": data,
    }


def drawing_document(path):
    """기존 도면 JSON을 현재 Tool의 도면 구조로 변환한다."""
    data = load_json(path)

    if "characteristics" not in data:
        data = {
            **data,
            "characteristics": [
                {
                    "nominal_mm": number(
                        data.get("diameter")
                    ),
                    "tolerance_mm": number(
                        data.get("tolerance")
                    ),
                }
            ],
        }

    return document(
        "DRAWING",
        path.name,
        data,
    )


def build_case_data(
    config,
    lot_row,
    inspections,
    drawings,
):
    """한 Lot에 대한 Case 정보를 구성한다."""
    lot_no = lot_row["lot_id"]
    documents = list(drawings)

    for row in inspections:
        # lot_id: 해당 검사 기록을 연결할 대상 Lot.
        # document_lot_id: 검사 문서에 실제 기재된 Lot.
        if row.get("lot_id") != lot_no:
            continue

        structured = {
            **row,
            "lot_no": (
                row.get("document_lot_id")
                or row.get("lot_id")
            ),
            "revision": (
                row.get("document_revision")
                or None
            ),
            "measured_mm": number(
                row.get("diameter")
            ),
        }

        documents.append(
            document(
                "INSPECTION_REPORT",
                "inspection.csv",
                structured,
            )
        )

    return {
        "case": {
            "case_id": config["case_id"],
            "part_no": config["part_id"],
            "drawing_revision": config["new_revision"],
        },
        "lot": {
            **lot_row,
            "lot_no": lot_no,
            "production_date": (
                lot_row.get("production_date")
                or None
            ),
            "effectivity_date": (
                lot_row.get("effectivity_date")
                or config.get("effectivity")
            ),
        },
        "documents": documents,
    }


def run_case(folder):
    config = load_json(
        folder / "case.json"
    )
    case_id = config["case_id"]

    lots = load_csv(
        folder / "lot.csv"
    )
    inspections = load_csv(
        folder / "inspection.csv"
    )

    if not lots:
        raise ValueError(
            "lot.csv에 Lot이 없습니다."
        )

    lot_ids = [
        row["lot_id"]
        for row in lots
    ]

    if len(set(lot_ids)) != len(lots):
        raise ValueError(
            "lot.csv에 중복 Lot ID가 있습니다."
        )

    if any(
        row.get("part_no") != config["part_id"]
        for row in lots
    ):
        raise ValueError(
            "Case와 Lot의 Part 번호가 다릅니다."
        )

    drawings = [
        drawing_document(folder / name)
        for name in (
            "rev_b.json",
            "rev_c.json",
        )
    ]

    warnings = {
        "기존 자료에는 별도 소재/열처리성적서가 없어 "
        "문서로 추가하지 않았습니다."
    }

    if any(
        any(
            row.get(key)
            for key in (
                "material",
                "heat_treatment",
                "heat_no",
            )
        )
        for row in inspections
    ):
        warnings.add(
            "현재 Tool은 검사 CSV의 재질/열처리/Heat를 "
            "성적서 값으로 읽지 않습니다."
        )

    if config.get("expected_heat_no"):
        warnings.add(
            "현재 Tool은 expected_heat_no 기준 비교를 "
            "지원하지 않습니다."
        )

    results = []
    excluded = []

    print(f"\n===== {case_id} =====")

    for row in lots:
        case_data = build_case_data(
            config,
            row,
            inspections,
            drawings,
        )

        # 1. 설계변경 분석
        design_result = analyze_design_change(
            case_data,
            case_id=case_id,
        )

        # 2. 검증계획 생성
        plan_result = create_validation_plan(
            design_result["result"]["changes"],
            case_id,
        )

        # 3. 영향범위 추적
        impact_result = trace_impact(
            case_data,
            case_id=case_id,
        )

        scope = impact_result[
            "result"
        ]["impact_status"]

        if impact_result.get("missing_items"):
            warnings.add(
                "생산일/Effectivity 누락: "
                "영향범위가 REVIEW_REQUIRED입니다."
            )

        # 4. 품질검증
        quality_result = validate_quality(
            case_data,
            affected_lots=impact_result[
                "result"
            ]["affected_lots"],
            case_id=case_id,
            required_documents=plan_result[
                "result"
            ]["required_documents"],
        )

        # 5. 후속조치 생성
        followup_result = handle_followup(
            quality_result,
            case_id,
        )

        lot_results = quality_result[
            "result"
        ]["lot_results"]

        actions = followup_result[
            "result"
        ]["actions"]

        print(
            f"Lot {row['lot_id']}: {scope}"
        )

        if scope == "BEFORE_EFFECTIVITY":
            if lot_results or actions:
                raise AssertionError(
                    "적용 전 Lot에 판정/후속조치가 "
                    "생성됐습니다."
                )

            excluded.append(
                row["lot_id"]
            )

        elif not lot_results:
            raise AssertionError(
                "검증 대상 Lot의 판정이 없습니다."
            )

        results.extend(lot_results)

        for item in lot_results:
            print(
                f"  {item['decision']} / "
                f"{item['issue_code']}: "
                f"{item['reason']}"
            )

        print(
            "  후속조치:",
            [
                action["action"]
                for action in actions
            ],
        )

    expected_decision = config[
        "expected_decision"
    ]

    expected_issue = config.get(
        "expected_issue_code",
        EXPECTED_ISSUES[case_id],
    )

    # 판정과 원인이 모두 일치해야 성공.
    passed = bool(results) and all(
        item["decision"] == expected_decision
        and item["issue_code"] == expected_issue
        for item in results
    )

    # VAL-009는 변경 전 Lot 제외 여부까지 확인.
    if case_id == "VAL-009":
        actual_lot_ids = [
            item["lot_id"]
            for item in results
        ]

        passed = (
            passed
            and excluded == ["LOT009A"]
            and actual_lot_ids == ["LOT009B"]
        )

    print(
        f"예상: {expected_decision} / "
        f"{expected_issue}"
    )

    for warning in sorted(warnings):
        print(
            "주의:",
            warning,
        )

    print(
        "TEST RESULT:",
        "PASS" if passed else "FAIL",
    )

    return passed


def main():
    passed_count = 0

    for index in range(1, 10):
        case_name = f"VAL-{index:03d}"

        folder = (
            ROOT
            / "data"
            / "validation_cases"
            / case_name
        )

        try:
            passed_count += int(
                run_case(folder)
            )

        except Exception as exc:
            print(
                f"\n{case_name}: ERROR "
                f"{type(exc).__name__}: {exc}"
            )

    print(
        f"\n총 9개: PASS {passed_count}, "
        f"FAIL/ERROR {9 - passed_count}"
    )

    print(
        "VAL-010은 기존 실행 범위 밖이므로 "
        "이번에는 실행하지 않습니다."
    )

    return 0 if passed_count == 9 else 1


if __name__ == "__main__":
    raise SystemExit(main())