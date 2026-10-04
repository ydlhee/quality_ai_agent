import importlib
import pkgutil
import sqlite3
from pathlib import Path

import database

TEST_DB = Path("database/agent_dynamic_test.db").resolve()
ORIGINAL_DB = Path("database/sample_lots.db").resolve()

if not TEST_DB.is_file():
    raise FileNotFoundError("테스트 DB가 없습니다.")

if TEST_DB == ORIGINAL_DB:
    raise RuntimeError("원본 DB를 테스트 DB로 사용할 수 없습니다.")

# DB 파일 자체의 유효성을 확인한다.
with sqlite3.connect(f"file:{TEST_DB.as_posix()}?mode=rw", uri=True) as conn:
    if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise RuntimeError("테스트 DB 무결성 검사 실패")

# 모든 database 하위 모듈을 불러와 DB 경로를 테스트용으로 변경한다.
# 파일에 저장된 DB_PATH 값은 수정하지 않는다.
patched = []

for module_info in pkgutil.iter_modules(database.__path__):
    name = module_info.name

    # 테스트 및 데이터 초기화 스크립트는 자동으로 불러오지 않는다.
    if name.startswith(("test_", "import_", "reset_")):
        continue

    module = importlib.import_module(f"database.{name}")

    if hasattr(module, "DB_PATH"):
        module.DB_PATH = TEST_DB
        patched.append(name)

print("TEST_DB:", TEST_DB)
print("PATCHED_MODULES:", ", ".join(patched))
# 테스트 도중 원본 DB에 접근하면 즉시 중단한다.
original_connect = sqlite3.connect

def safe_connect(database_path, *args, **kwargs):
    if isinstance(database_path, (str, Path)):
        path = str(database_path)

        if not path.startswith("file:"):
            if Path(path).resolve() == ORIGINAL_DB:
                raise RuntimeError(
                    "안전장치 작동: 원본 DB 접근을 차단했습니다."
                )

    return original_connect(database_path, *args, **kwargs)

sqlite3.connect = safe_connect

# DB 연결을 변경한 다음 Agent를 불러온다.
import agent.runner as runner

# Control only the LLM responses for this integration test.
def mock_initial_review(state):
    return {
        "additional_checks": [],
        "reason": "Initial mandatory plan only",
        "decision_source": "TEST_MOCK",
    }

def mock_dynamic_replan(state):
    return {
        "replanning_required": True,
        "reason": "Verify heat treatment after material change",
        "suggested_checks": [
            {
                "document_type": "HEAT_TREATMENT_CERTIFICATE",
                "reason": "Additional heat treatment verification",
            }
        ],
        "decision_source": "TEST_MOCK",
    }

runner.review_validation_plan = mock_initial_review
runner.replan_from_quality_result = mock_dynamic_replan

original_validate = runner.validate_quality
validation_calls = []

def tracked_validate(*args, **kwargs):
    validation_calls.append(
        list(kwargs.get("required_documents") or [])
    )
    return original_validate(*args, **kwargs)

runner.validate_quality = tracked_validate

from agent.runner import run_case

state = run_case("CASE-001")

print("\n===== AGENT UPGRADE TEST =====")
print("FINAL_DECISION:", state.get("decision"))
print("CASE_STATUS:", state.get("case_status"))
print("PLAN_REVISION:", state.get("plan_revision"))
print("REPLANNING_COMPLETED:", state.get("replanning_completed"))

print("\n===== AGENT TRACE =====")
for entry in state.get("agent_trace", []):
    print(
        entry.get("step"),
        entry.get("tool"),
        entry.get("decision_source"),
        entry.get("result"),
    )

print("\n===== PLAN ADJUSTMENTS =====")
for adjustment in state.get("plan_adjustments", []):
    print(adjustment)

print("\n===== DYNAMIC REPLAN ASSERTIONS =====")

dynamic_adjustments = [
    item for item in state.get("plan_adjustments", [])
    if item.get("type") == "DYNAMIC_REPLAN"
]

assert state.get("replanning_completed") is True
assert state.get("plan_revision") == 1
assert len(validation_calls) == 2
assert len(dynamic_adjustments) == 1

added = dynamic_adjustments[0]["additional_checks"]
assert any(
    item["document_type"] == "HEAT_TREATMENT_CERTIFICATE"
    for item in added
)

assert "HEAT_TREATMENT_CERTIFICATE" not in validation_calls[0]
assert "HEAT_TREATMENT_CERTIFICATE" in validation_calls[1]

print("VALIDATION_CALLS:", validation_calls)
print("FINAL_DECISION:", state.get("decision"))
print("ALL_ASSERTIONS_PASSED")
