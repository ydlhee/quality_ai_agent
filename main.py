import json
from pathlib import Path

from tools.drawing_compare import analyze_design_change
from tools.verification_plan import create_validation_plan
from tools.lot_trace import trace_impact
from tools.quality_verify import validate_quality
from tools.followup import handle_followup


# 실행할 테스트 Case
case_folder = Path("data/test_cases/CASE-001")


# Case 정보 불러오기
with open(
    case_folder / "case.json",
    "r",
    encoding="utf-8"
) as file:
    case_data = json.load(file)


case_id = case_data["case_id"]
part_id = case_data["part_id"]
old_revision = case_data["old_revision"]
new_revision = case_data["new_revision"]

effectivity = case_data.get("effectivity")
expected_material = case_data.get("expected_material")
expected_heat_treatment = case_data.get(
    "expected_heat_treatment"
)
expected_heat_no = case_data.get("expected_heat_no")

nominal = case_data["nominal"]
tolerance = case_data["tolerance"]


# 1. 설계변경 분석
design_result = analyze_design_change(
    str(case_folder / "rev_b.json"),
    str(case_folder / "rev_c.json"),
    case_id
)

print("===== 1. 설계변경 분석 =====")
print(design_result)


# 2. 검증계획 생성
changes = design_result["result"]["changes"]

plan_result = create_validation_plan(
    changes,
    case_id,
    expected_heat_no=expected_heat_no
)

print("\n===== 2. 검증계획 =====")
print(plan_result)


# 3. 영향범위 추적
impact_result = trace_impact(
    str(case_folder / "lot.csv"),
    part_id,
    old_revision,
    case_id,
    effectivity=effectivity
)

print("\n===== 3. 영향범위 추적 =====")
print(impact_result)


# 영향 Lot ID만 추출
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
    case_id,
    expected_revision=new_revision,
    expected_material=expected_material,
    expected_heat_treatment=expected_heat_treatment,
    expected_heat_no=expected_heat_no
)

print("\n===== 4. 품질검증 =====")
print(quality_result)


# 5. 후속조치
followup_result = handle_followup(
    quality_result,
    case_id
)

print("\n===== 5. 후속조치 =====")
print(followup_result)