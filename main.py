from tools.drawing_compare import analyze_design_change
from tools.verification_plan import create_validation_plan
from tools.lot_trace import trace_impact
from tools.quality_verify import validate_quality
from tools.followup import handle_followup


CASE_ID = "CASE-001"


# 1. 설계변경 분석
design_result = analyze_design_change(
    "data/rev_b.json",
    "data/rev_c.json",
    CASE_ID
)

print("===== 1. 설계변경 분석 =====")
print(design_result)


# 2. 검증계획 생성
changes = design_result["result"]["changes"]

plan_result = create_validation_plan(
    changes,
    CASE_ID
)

print("\n===== 2. 검증계획 =====")
print(plan_result)


# 3. 영향범위 추적
impact_result = trace_impact(
    "data/lot.csv",
    "A1001",
    "B",
    CASE_ID
)

print("\n===== 3. 영향범위 추적 =====")
print(impact_result)


# Lot ID만 품질검증 함수에 전달
affected_lots = [
    lot["lot_id"]
    for lot in impact_result["result"]["affected_lots"]
]


# 4. 품질검증
quality_result = validate_quality(
    "data/inspection.csv",
    affected_lots,
    20.0,
    0.1,
    CASE_ID
)

print("\n===== 4. 품질검증 =====")
print(quality_result)


# 5. 후속조치
followup_result = handle_followup(
    quality_result,
    CASE_ID
)

print("\n===== 5. 후속조치 =====")
print(followup_result)