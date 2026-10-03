import copy
import json
from pathlib import Path

from tools.drawing_compare import analyze_design_change
from tools.verification_plan import create_validation_plan
from tools.lot_trace import trace_impact
from tools.quality_verify import validate_quality


ROOT = Path(__file__).resolve().parent

path = (
    ROOT
    / "data"
    / "final_validation_cases"
    / "QA-009"
    / "scenario.json"
)

scenario = json.loads(
    path.read_text(encoding="utf-8")
)

data = copy.deepcopy(
    scenario["phases"][0]["case_data"]
)

case_id = data["case"]["case_id"]

# 검사성적서 Lot 번호만 올바른 대상 Lot으로 정정
for doc in data["documents"]:
    if doc.get("document_type") == "INSPECTION_REPORT":
        doc["structured_data"]["lot_no"] = "LOT-QA-009"


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

row = quality["result"]["lot_results"][0]

print("decision   :", row["decision"])
print("issue_code :", row["issue_code"])
print("reason     :", row["reason"])