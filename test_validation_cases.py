import json
from pathlib import Path

from tools.drawing_compare import analyze_design_change
from tools.verification_plan import create_validation_plan
from tools.lot_trace import trace_impact
from tools.quality_verify import validate_quality
from tools.followup import handle_followup


ROOT = Path(__file__).resolve().parent


def run_scenario(path):
    scenario = json.loads(
        path.read_text(encoding="utf-8")
    )

    for phase in scenario["phases"]:
        data = phase["case_data"]
        case_id = data["case"]["case_id"]

        design = analyze_design_change(
            data,
            case_id=case_id,
        )
        assert not design["missing_items"], "도면 정보 누락"

        plan = create_validation_plan(
            design["result"]["changes"],
            case_id,
        )

        impact = trace_impact(
            data,
            case_id=case_id,
        )
        assert not impact["missing_items"], "Lot 날짜 정보 누락"

        quality = validate_quality(
            data,
            affected_lots=impact["result"]["affected_lots"],
            case_id=case_id,
            required_documents=plan["result"]["required_documents"],
        )

        followup = handle_followup(
            quality,
            case_id,
        )

        expected = phase["expected"]
        scope = impact["result"]["impact_status"]
        rows = quality["result"]["lot_results"]
        actions = followup["result"]["actions"]

        assert scope == expected["scope"], f"영향범위: {scope}"

        if expected["decision"] == "EXCLUDED":
            assert not rows and not actions, (
                "적용 전 Lot에 판정/조치 발생"
            )
            print(
                f"  {phase['name']}: 적용 전 Lot 정상 제외"
            )
            continue

        assert len(rows) == 1, f"판정 개수: {len(rows)}"

        row = rows[0]
        actual = (
            row["decision"],
            row["issue_code"],
        )
        target = (
            expected["decision"],
            expected["issue_code"],
        )

        print(
            f"  {phase['name']}: 실제 {actual}, 예상 {target}"
        )

        assert actual == target, (
            f"판정/원인 불일치: {actual} != {target}"
        )

        assert row["lot_id"] == data["lot"]["lot_no"], (
            "판정 Lot 불일치"
        )

        assert len(actions) == 1, "후속조치 개수 오류"

        expected_action = {
            "PASS": "NONE",
            "HOLD": "CORRECTION_REQUEST",
            "REJECT": "REJECT_LOT",
        }[row["decision"]]

        assert actions[0]["action"] == expected_action, (
            "후속조치 불일치"
        )

        assert bool(quality["evidence"]), "판정 근거 없음"


def main():
    success = 0

    for index in range(1, 16):
        name = f"VAL-{index:03d}"
        path = (
            ROOT
            / "data"
            / "validation_cases_v2"
            / name
            / "scenario.json"
        )

        print(f"\\n===== {name} =====")

        try:
            run_scenario(path)
            success += 1
            print("TEST RESULT: PASS")

        except Exception as exc:
            print(
                f"TEST RESULT: FAIL / "
                f"{type(exc).__name__}: {exc}"
            )

    print(
        f"\\n총 15개: PASS {success}, FAIL {15 - success}"
    )
    print(
        "가상 구조화 자료 기반 Tool 테스트입니다. "
        "Gmail/DB 통합 검증은 별도입니다."
    )

    return 0 if success == 15 else 1


if __name__ == "__main__":
    raise SystemExit(main())
