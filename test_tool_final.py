import json
from pathlib import Path
from time import perf_counter

from tools.drawing_compare import analyze_design_change
from tools.verification_plan import create_validation_plan
from tools.lot_trace import trace_impact
from tools.quality_verify import validate_quality
from tools.followup import handle_followup


ROOT = Path(__file__).resolve().parent


def timed_call(name, func, *args, **kwargs):
    start = perf_counter()

    try:
        result = func(*args, **kwargs)
        elapsed_ms = (perf_counter() - start) * 1000

        print(
            f"[PASS] {name:<24} "
            f"{elapsed_ms:8.3f} ms"
        )

        return result, elapsed_ms, None

    except Exception as exc:
        elapsed_ms = (perf_counter() - start) * 1000

        print(
            f"[FAIL] {name:<24} "
            f"{elapsed_ms:8.3f} ms / "
            f"{type(exc).__name__}: {exc}"
        )

        return None, elapsed_ms, exc


def load_phase(case_name, phase_index=0):
    path = (
        ROOT
        / "data"
        / "validation_cases_v2"
        / case_name
        / "scenario.json"
    )

    scenario = json.loads(
        path.read_text(encoding="utf-8")
    )

    return scenario["phases"][phase_index]


def check_common_output(name, result):
    assert isinstance(result, dict), (
        f"{name}: 반환값이 dict가 아님"
    )

    assert "status" in result, (
        f"{name}: status 없음"
    )

    assert "result" in result, (
        f"{name}: result 없음"
    )

    assert "evidence" in result, (
        f"{name}: evidence 없음"
    )

    assert "missing_items" in result, (
        f"{name}: missing_items 없음"
    )


def run_pipeline(case_name, expected_decision):
    print(
        f"\n========== {case_name} / "
        f"{expected_decision} =========="
    )

    phase = load_phase(case_name)

    data = phase["case_data"]
    case_id = data["case"]["case_id"]

    times = {}

    # 1. 설계변경 분석
    design, times["analyze_design_change"], error = timed_call(
        "analyze_design_change",
        analyze_design_change,
        data,
        case_id=case_id,
    )

    assert error is None
    check_common_output(
        "analyze_design_change",
        design,
    )

    # 2. 검증계획
    plan, times["create_validation_plan"], error = timed_call(
        "create_validation_plan",
        create_validation_plan,
        design["result"]["changes"],
        case_id,
    )

    assert error is None
    check_common_output(
        "create_validation_plan",
        plan,
    )

    # 3. 영향범위
    impact, times["trace_impact"], error = timed_call(
        "trace_impact",
        trace_impact,
        data,
        case_id=case_id,
    )

    assert error is None
    check_common_output(
        "trace_impact",
        impact,
    )

    # 4. 품질검증
    quality, times["validate_quality"], error = timed_call(
        "validate_quality",
        validate_quality,
        data,
        affected_lots=impact[
            "result"
        ]["affected_lots"],
        case_id=case_id,
        required_documents=plan[
            "result"
        ]["required_documents"],
    )

    assert error is None
    check_common_output(
        "validate_quality",
        quality,
    )

    rows = quality["result"]["lot_results"]

    assert len(rows) == 1, (
        f"품질판정 결과 개수 오류: {len(rows)}"
    )

    decision = rows[0]["decision"]

    assert decision == expected_decision, (
        f"예상 {expected_decision}, "
        f"실제 {decision}"
    )

    # 5. 후속조치
    followup, times["handle_followup"], error = timed_call(
        "handle_followup",
        handle_followup,
        quality,
        case_id,
    )

    assert error is None
    check_common_output(
        "handle_followup",
        followup,
    )

    actions = followup["result"]["actions"]

    expected_action = {
        "PASS": "NONE",
        "HOLD": "CORRECTION_REQUEST",
        "REJECT": "REJECT_LOT",
    }[expected_decision]

    assert actions[0]["action"] == expected_action

    total = sum(times.values())

    print(
        f"결과: {decision} / "
        f"후속조치: {actions[0]['action']}"
    )

    print(
        f"5개 Tool 총 실행시간: "
        f"{total:.3f} ms"
    )

    return times


def run_exception_tests():
    print(
        "\n========== 예외 처리 점검 =========="
    )

    success = 0
    total = 3

    # 1. 도면 정보 누락
    try:
        result = analyze_design_change(
            {
                "case": {
                    "case_id": "EXCEPTION-DRAWING"
                }
            },
            case_id="EXCEPTION-DRAWING",
        )

        assert isinstance(result, dict)
        assert result.get("missing_items")

        print(
            "[PASS] 도면 누락 → "
            "missing_items 반환"
        )

        success += 1

    except Exception as exc:
        print(
            "[FAIL] 도면 누락 처리 / "
            f"{type(exc).__name__}: {exc}"
        )

    # 2. Lot 정보 누락
    try:
        result = trace_impact(
            {
                "case": {
                    "case_id": "EXCEPTION-LOT"
                }
            },
            case_id="EXCEPTION-LOT",
        )

        assert isinstance(result, dict)
        assert result.get("missing_items")

        print(
            "[PASS] Lot 누락 → "
            "missing_items 반환"
        )

        success += 1

    except Exception as exc:
        print(
            "[FAIL] Lot 누락 처리 / "
            f"{type(exc).__name__}: {exc}"
        )

    # 3. 빈 품질검증 대상
    try:
        result = validate_quality(
            {
                "case": {
                    "case_id": "EXCEPTION-QUALITY"
                }
            },
            affected_lots=[],
            case_id="EXCEPTION-QUALITY",
            required_documents=[],
        )

        assert isinstance(result, dict)

        print(
            "[PASS] 검증 대상 없음 → "
            "예외 없이 반환"
        )

        success += 1

    except Exception as exc:
        print(
            "[FAIL] 빈 품질검증 처리 / "
            f"{type(exc).__name__}: {exc}"
        )

    print(
        f"예외 처리 결과: "
        f"PASS {success}, "
        f"FAIL {total - success}"
    )

    return success == total


def main():
    all_times = {
        "analyze_design_change": [],
        "create_validation_plan": [],
        "trace_impact": [],
        "validate_quality": [],
        "handle_followup": [],
    }

    tests = [
        ("VAL-001", "PASS"),
        ("VAL-002", "HOLD"),
        ("VAL-003", "REJECT"),
    ]

    pipeline_success = 0

    for case_name, decision in tests:
        try:
            times = run_pipeline(
                case_name,
                decision,
            )

            for name, elapsed in times.items():
                all_times[name].append(elapsed)

            pipeline_success += 1

            print("PIPELINE TEST: PASS")

        except Exception as exc:
            print(
                "PIPELINE TEST: FAIL / "
                f"{type(exc).__name__}: {exc}"
            )

    exception_ok = run_exception_tests()

    print(
        "\n========== 평균 실행시간 =========="
    )

    for name, values in all_times.items():
        if values:
            average = sum(values) / len(values)

            print(
                f"{name:<24} "
                f"{average:8.3f} ms"
            )

    print(
        "\n========== 최종 결과 =========="
    )

    print(
        f"PASS/HOLD/REJECT Pipeline: "
        f"{pipeline_success}/3"
    )

    print(
        "예외 처리: "
        + (
            "PASS"
            if exception_ok
            else "FAIL"
        )
    )

    final_ok = (
        pipeline_success == 3
        and exception_ok
    )

    print(
        "FINAL TOOL TEST: "
        + (
            "PASS"
            if final_ok
            else "FAIL"
        )
    )

    return 0 if final_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())