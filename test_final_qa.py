import json
from pathlib import Path
from time import perf_counter

from tools.drawing_compare import analyze_design_change
from tools.verification_plan import create_validation_plan
from tools.lot_trace import trace_impact
from tools.quality_verify import validate_quality
from tools.followup import handle_followup


ROOT = Path(__file__).resolve().parent


def run_case(name):
    path = (
        ROOT
        / "data"
        / "final_validation_cases"
        / name
        / "scenario.json"
    )

    scenario = json.loads(
        path.read_text(encoding="utf-8")
    )

    phase = scenario["phases"][0]
    data = phase["case_data"]
    expected = phase.get("expected", {})

    case_id = data["case"]["case_id"]

    start = perf_counter()

    design = analyze_design_change(
        data,
        case_id=case_id,
    )

    plan = create_validation_plan(
        design["result"]["changes"],
        case_id,
    )

    impact = trace_impact(
        data,
        case_id=case_id,
    )

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

    elapsed_ms = (perf_counter() - start) * 1000

    rows = quality["result"]["lot_results"]
    impact_status = impact["result"].get("impact_status")

    if rows:
        row = rows[0]

        decision = row.get("decision")
        issue_code = row.get("issue_code")
        reason = row.get("reason")

    elif impact_status == "BEFORE_EFFECTIVITY":
        decision = "EXCLUDED"
        issue_code = None
        reason = "Effectivity 이전 생산 Lot으로 검증 대상 제외"

    else:
        decision = None
        issue_code = None
        reason = "판정 결과 없음"

    expected_decision = expected.get("decision")
    expected_issue = expected.get("issue_code")

    print(f"\n===== {name} =====")
    print("actual decision :", decision)
    print("actual issue    :", issue_code)
    print("reason          :", reason)
    print("expected        :", expected_decision, "/", expected_issue)
    print(f"execution       : {elapsed_ms:.3f} ms")

    if expected_decision is None:
        result = "TEAM_DECISION_REQUIRED"
    elif (
        decision == expected_decision
        and issue_code == expected_issue
    ):
        result = "PASS"
    else:
        result = "FAIL"

    print("comparison      :", result)

    return {
        "case": name,
        "decision": decision,
        "issue_code": issue_code,
        "reason": reason,
        "expected_decision": expected_decision,
        "expected_issue": expected_issue,
        "execution_ms": elapsed_ms,
        "comparison": result,
    }


results = []

for i in range(1, 11):
    name = f"QA-{i:03d}"
    results.append(run_case(name))


print("\n========== FINAL SUMMARY ==========")

for r in results:
    print(
        f"{r['case']} | "
        f"{r['decision']} | "
        f"{r['issue_code']} | "
        f"{r['execution_ms']:.3f} ms | "
        f"{r['comparison']}"
    )