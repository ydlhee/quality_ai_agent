import json
from pathlib import Path

from tools.drawing_compare import analyze_design_change
from tools.verification_plan import create_validation_plan
from tools.lot_trace import trace_impact
from tools.quality_verify import validate_quality
from tools.followup import handle_followup


def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def run_case(case_folder):

    case_data = load_json(case_folder / "case.json")

    case_id = case_data["case_id"]
    part_id = case_data["part_id"]
    old_revision = case_data["old_revision"]
    nominal = case_data["nominal"]
    tolerance = case_data["tolerance"]
    expected_decision = case_data["expected_decision"]

    # 1. 설계변경 분석
    design_result = analyze_design_change(
        str(case_folder / "rev_b.json"),
        str(case_folder / "rev_c.json"),
        case_id
    )

    # 2. 검증계획 생성
    changes = design_result["result"]["changes"]

    plan_result = create_validation_plan(
        changes,
        case_id
    )

    # 3. 영향범위 추적
    impact_result = trace_impact(
        str(case_folder / "lot.csv"),
        part_id,
        old_revision,
        case_id
    )

    affected_lots = [
        lot["lot_id"]
        for lot in impact_result["result"]["affected_lots"]
    ]

    # 4. 품질검증
    quality_result = validate_quality(
        str(case_folder / "inspection.csv"),
        affected_lots,
        nominal,
        tolerance,
        case_id
    )

    # 5. 후속조치
    followup_result = handle_followup(
        quality_result,
        case_id
    )

    actual_decision = (
        quality_result["result"]["lot_results"][0]["decision"]
    )

    print("\n================================")
    print(f"{case_id}")
    print("================================")

    print("설계변경:")
    print(design_result["result"]["changes"])

    print("\n검증계획:")
    print(plan_result["result"]["validation_tasks"])

    print("\n영향 Lot:")
    print(impact_result["result"]["affected_lots"])

    print("\n품질판정:")
    print(quality_result["result"]["lot_results"])

    print("\n후속조치:")
    print(followup_result["result"]["actions"])

    print("\n예상 판정 :", expected_decision)
    print("실제 판정 :", actual_decision)

    if actual_decision == expected_decision:
        print("TEST RESULT : PASS")
    else:
        print("TEST RESULT : FAIL")


base_path = Path("data/test_cases")

for case_name in [
    "CASE-001",
    "CASE-002",
    "CASE-003"
]:
    run_case(base_path / case_name)