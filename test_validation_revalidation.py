import json
from pathlib import Path

from tools.drawing_compare import analyze_design_change
from tools.verification_plan import create_validation_plan
from tools.lot_trace import trace_impact
from tools.quality_verify import validate_quality
from tools.followup import handle_followup


def load_json(file_path):
    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


case_folder = Path(
    "data/validation_cases/VAL-010"
)

case_data = load_json(
    case_folder / "case.json"
)


case_id = case_data["case_id"]
part_id = case_data["part_id"]

old_revision = case_data["old_revision"]
new_revision = case_data["new_revision"]

nominal = case_data["nominal"]
tolerance = case_data["tolerance"]

expected_initial_decision = (
    case_data["expected_initial_decision"]
)

expected_revalidation_decision = (
    case_data["expected_revalidation_decision"]
)


# ==========================================
# 1. 설계변경 분석
# ==========================================

design_result = analyze_design_change(
    str(case_folder / "rev_b.json"),
    str(case_folder / "rev_c.json"),
    case_id
)


# ==========================================
# 2. 검증계획 생성
# ==========================================

changes = design_result[
    "result"
]["changes"]

plan_result = create_validation_plan(
    changes,
    case_id
)


# ==========================================
# 3. 영향범위 추적
# ==========================================

impact_result = trace_impact(
    str(case_folder / "lot.csv"),
    part_id,
    old_revision,
    case_id
)


affected_lots = [
    lot["lot_id"]
    for lot in impact_result[
        "result"
    ]["affected_lots"]
]


# ==========================================
# 4. 최초 품질검증
# ==========================================

initial_quality_result = validate_quality(
    str(
        case_folder
        / "inspection_initial.csv"
    ),
    affected_lots,
    nominal,
    tolerance,
    case_id,
    expected_revision=new_revision
)


initial_followup_result = handle_followup(
    initial_quality_result,
    case_id
)


initial_lot_result = (
    initial_quality_result[
        "result"
    ]["lot_results"][0]
)

initial_decision = (
    initial_lot_result[
        "decision"
    ]
)


initial_action = (
    initial_followup_result[
        "result"
    ]["actions"][0]
)


# ==========================================
# 5. 재검증 필요 여부 확인
# ==========================================

revalidation_info = (
    initial_action[
        "revalidation"
    ]
)

revalidation_required = (
    revalidation_info[
        "required"
    ]
)

revalidation_tool = (
    revalidation_info[
        "tool"
    ]
)


# ==========================================
# 6. 보완자료 수신 후 재검증
# ==========================================

if (
    revalidation_required
    and revalidation_tool
    == "validate_quality"
):

    revalidation_quality_result = (
        validate_quality(
            str(
                case_folder
                / "inspection_corrected.csv"
            ),
            affected_lots,
            nominal,
            tolerance,
            case_id,
            expected_revision=new_revision
        )
    )

    revalidation_followup_result = (
        handle_followup(
            revalidation_quality_result,
            case_id
        )
    )

    revalidation_lot_result = (
        revalidation_quality_result[
            "result"
        ]["lot_results"][0]
    )

    revalidation_decision = (
        revalidation_lot_result[
            "decision"
        ]
    )

else:

    revalidation_quality_result = None
    revalidation_followup_result = None
    revalidation_decision = (
        "REVALIDATION_NOT_EXECUTED"
    )


# ==========================================
# 7. 결과 출력
# ==========================================

print("\n================================")
print("VAL-010 재검증 테스트")
print("================================")


print("\n[1차 품질검증]")

print(
    initial_quality_result[
        "result"
    ]["lot_results"]
)


print("\n[1차 후속조치]")

print(
    initial_followup_result[
        "result"
    ]["actions"]
)


print("\n[재검증 정보]")

print(
    revalidation_info
)


print("\n[보완자료 수신]")

print(
    "inspection_corrected.csv"
)


print("\n[2차 품질검증]")

if revalidation_quality_result:

    print(
        revalidation_quality_result[
            "result"
        ]["lot_results"]
    )

else:

    print(
        "재검증이 실행되지 않았습니다."
    )


print("\n[2차 후속조치]")

if revalidation_followup_result:

    print(
        revalidation_followup_result[
            "result"
        ]["actions"]
    )

else:

    print(
        "후속조치 없음"
    )


print(
    "\n예상 최초 판정 :",
    expected_initial_decision
)

print(
    "실제 최초 판정 :",
    initial_decision
)


print(
    "\n예상 재검증 판정 :",
    expected_revalidation_decision
)

print(
    "실제 재검증 판정 :",
    revalidation_decision
)


if (
    initial_decision
    == expected_initial_decision
    and revalidation_decision
    == expected_revalidation_decision
):

    print(
        "\nREVALIDATION TEST RESULT : PASS"
    )

else:

    print(
        "\nREVALIDATION TEST RESULT : FAIL"
    )