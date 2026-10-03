"""추가 구조화 테스트 자료와 정답표 생성."""

import copy
import json
from datetime import date
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

SOURCE = (
    ROOT
    / "data"
    / "validation_cases_v2"
    / "VAL-001"
    / "scenario.json"
)

OUTPUT = ROOT / "data" / "final_validation_cases"


SPECS = [
    (
        "QA-001",
        "Effectivity 당일 새 Revision 적용",
        "PASS",
        "NO_ISSUE",
    ),
    (
        "QA-002",
        "Effectivity 전날 구 Revision 생산",
        "EXCLUDED",
        None,
    ),
    (
        "QA-003",
        "공차 하한값 19.90",
        "PASS",
        "NO_ISSUE",
    ),
    (
        "QA-004",
        "공차 상한값 20.10",
        "PASS",
        "NO_ISSUE",
    ),
    (
        "QA-005",
        "공차 상한 초과 20.11",
        "REJECT",
        "DIMENSION_OUT_OF_TOLERANCE",
    ),
    (
        "QA-006",
        "Lot C, 검사성적서만 B",
        "HOLD",
        "REVISION_MISMATCH",
    ),
    (
        "QA-007",
        "요구 재질과 소재성적서 불일치",
        "REJECT",
        "MATERIAL_MISMATCH",
    ),
    (
        "QA-008",
        "재질 변경 후 필수 소재성적서 누락",
        "HOLD",
        "REQUIRED_DOCUMENT_MISSING",
    ),
    (
        "QA-009",
        "검사성적서가 다른 Lot을 가리킴",
        "HOLD",
        "LOT_ID_MISMATCH",
    ),
    (
        "QA-010",
        "구버전 검사성적서와 공차 초과 동시 발생",
        "REJECT",
        "DIMENSION_OUT_OF_TOLERANCE",
    ),
]


def encode(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    ) + "\n"


def make_case(template, spec):
    case_id, title, decision, issue = spec

    data = copy.deepcopy(template)
    lot_no = "LOT-" + case_id

    data["case"] = {
        "case_id": case_id,
        "part_no": "A1001",
        "drawing_revision": "C",
    }

    data["lot"] = {
        "lot_no": lot_no,
        "part_no": "A1001",
        "revision": "C",
        "production_date": "2026-09-20",
        "effectivity_date": "2026-09-15",
    }

    documents = data["documents"]

    def find_document(kind, revision=None):
        for doc in documents:
            if doc["document_type"] != kind:
                continue

            if revision is not None:
                if doc["structured_data"].get("revision") != revision:
                    continue

            return doc

        raise ValueError(
            f"기준 자료에 필요한 문서가 없습니다: {kind}, {revision}"
        )

    old = find_document("DRAWING", "B")
    new = find_document("DRAWING", "C")
    inspection = find_document("INSPECTION_REPORT")
    material = find_document("MATERIAL_CERTIFICATE")
    heat = find_document("HEAT_TREATMENT_CERTIFICATE")

    documents = [
        old,
        new,
        inspection,
        material,
        heat,
    ]
    data["documents"] = documents

    for doc in documents:
        doc["file_name"] = case_id + "_" + doc["file_name"]
        doc["document_stage"] = "INITIAL"
        doc["structured_data"]["part_no"] = "A1001"

        if doc["document_type"] != "DRAWING":
            doc["structured_data"]["lot_no"] = lot_no

    for doc, revision, tolerance in (
        (old, "B", 0.2),
        (new, "C", 0.1),
    ):
        doc["structured_data"].update(
            revision=revision,
            material="AL7075",
            heat_treatment="T6",
            characteristics=[
                {
                    "nominal_mm": 20.0,
                    "tolerance_mm": tolerance,
                }
            ],
        )

    inspection["structured_data"].update(
        revision="C",
        measured_mm=20.05,
    )

    material["structured_data"].update(
        material="AL7075",
        heat_no="HEAT-100",
    )

    heat["structured_data"].update(
        heat_treatment="T6",
        heat_no="HEAT-100",
    )

    note = (
        "지정 항목 이외에는 정상 조건이며, "
        "실제 Tool 판정은 아직 실행하지 않았습니다."
    )

    if case_id == "QA-001":
        data["lot"]["production_date"] = "2026-09-15"

    elif case_id == "QA-002":
        data["lot"].update(
            production_date="2026-09-14",
            revision="B",
        )
        inspection["structured_data"]["revision"] = "B"

        note = (
            "새 Revision 변경영향 대상에서 제외합니다. "
            "구 Revision의 품질 PASS를 의미하지 않습니다."
        )

    elif case_id in ("QA-003", "QA-004", "QA-005"):
        inspection["structured_data"]["measured_mm"] = {
            "QA-003": 19.90,
            "QA-004": 20.10,
            "QA-005": 20.11,
        }[case_id]

    elif case_id == "QA-006":
        inspection["structured_data"]["revision"] = "B"

    elif case_id in ("QA-007", "QA-008"):
        new["structured_data"]["material"] = "AL2024"

        if case_id == "QA-008":
            documents.remove(material)

            note = (
                "재질 변경으로 소재성적서가 필수입니다. "
                "해당 문서 자체를 제출 목록에서 제외했습니다."
            )

    elif case_id == "QA-009":
        inspection["structured_data"]["lot_no"] = "LOT-OTHER-999"

        note = (
            "검사성적서의 Lot 번호가 대상 Lot과 달라 "
            "대상 Lot의 검사 결과를 확인할 수 없으므로 HOLD합니다. "
            "올바른 검사성적서 제출 후 재검증합니다."
        )

    elif case_id == "QA-010":
        inspection["structured_data"].update(
            revision="B",
            measured_mm=20.11,
        )

        note = (
            "같은 Lot의 20.11은 구 공차 19.80~20.20 안이지만 "
            "새 공차 19.90~20.10 밖입니다. "
            "확인된 공차 초과가 문서 HOLD에 가려지는지 확인합니다."
        )

    production_date = date.fromisoformat(
        data["lot"]["production_date"]
    )
    effectivity_date = date.fromisoformat(
        data["lot"]["effectivity_date"]
    )

    in_scope = production_date >= effectivity_date

    scope = (
        "IN_EFFECTIVITY_SCOPE"
        if in_scope
        else "BEFORE_EFFECTIVITY"
    )

    required = new["structured_data"]
    characteristic = required["characteristics"][0]

    nominal = Decimal(
        str(characteristic["nominal_mm"])
    )
    tolerance = Decimal(
        str(characteristic["tolerance_mm"])
    )
    measured = Decimal(
        str(inspection["structured_data"]["measured_mm"])
    )

    lower = nominal - tolerance
    upper = nominal + tolerance

    evidence = []

    for index, doc in enumerate(documents):
        evidence.append(
            {
                "document_type": doc["document_type"],
                "file_name": doc["file_name"],
                "json_pointer": (
                    "/phases/0/case_data/documents/"
                    f"{index}/structured_data"
                ),
            }
        )

    received_types = {
        doc["document_type"]
        for doc in documents
    }

    missing = [
        kind
        for kind in (
            "DRAWING",
            "INSPECTION_REPORT",
            "MATERIAL_CERTIFICATE",
            "HEAT_TREATMENT_CERTIFICATE",
        )
        if kind not in received_types
    ]

    oracle_status = (
        "PENDING_TEAM_DECISION"
        if decision is None
        else "DEFINED"
    )

    answer = {
        "case_id": case_id,
        "title": title,
        "synthetic_fixture": True,
        "oracle_status": oracle_status,
        "expected": {
            "decision": decision,
            "issue_code": issue,
            "scope": scope,
        },
        "design_requirements": {
            "new_revision": "C",
            "effectivity": data["lot"]["effectivity_date"],
            "nominal_mm": str(nominal),
            "tolerance_mm": str(tolerance),
            "lower_mm": str(lower),
            "upper_mm": str(upper),
            "material": required["material"],
            "heat_treatment": required["heat_treatment"],
        },
        "actual_data": {
            "lot": copy.deepcopy(data["lot"]),
            "inspection": copy.deepcopy(
                inspection["structured_data"]
            ),
            "material_certificate": (
                copy.deepcopy(material["structured_data"])
                if material in documents
                else None
            ),
            "heat_certificate": copy.deepcopy(
                heat["structured_data"]
            ),
            "missing_document_types": missing,
        },
        "independent_checks": {
            "in_effectivity_scope": in_scope,
            "within_new_tolerance": lower <= measured <= upper,
            "inspection_lot_matches": (
                inspection["structured_data"]["lot_no"] == lot_no
            ),
        },
        "reason": note,
        "evidence": evidence,
        "actual_result": None,
        "execution_status": "NOT_RUN",
    }

    # 생성한 자료와 정답의 기본 조건 점검
    if decision == "PASS":
        if not in_scope or not lower <= measured <= upper or missing:
            raise ValueError(
                f"{case_id}: PASS 정답 조건 오류"
            )

    if issue == "DIMENSION_OUT_OF_TOLERANCE":
        if lower <= measured <= upper:
            raise ValueError(
                f"{case_id}: 공차 초과 자료 오류"
            )

    scenario = {
        "synthetic_fixture": True,
        "case_id": case_id,
        "title": title,
        "oracle_status": oracle_status,
        "phases": [
            {
                "name": "initial",
                "case_data": data,
                "expected": copy.deepcopy(
                    answer["expected"]
                ),
            }
        ],
    }

    return scenario, answer


def main():
    source = json.loads(
        SOURCE.read_text(encoding="utf-8-sig")
    )
    template = source["phases"][0]["case_data"]

    files = {}
    answers = []

    for spec in SPECS:
        scenario, answer = make_case(
            template,
            spec,
        )

        folder = OUTPUT / spec[0]

        files[folder / "scenario.json"] = encode(
            scenario
        )
        files[folder / "answer.json"] = encode(
            answer
        )

        answers.append(answer)

    files[OUTPUT / "answer_key.json"] = encode(
        answers
    )

    rows = [
        "# 추가 테스트 정답표",
        "",
        "가상 구조화 자료입니다. "
        "PDF 추출·DB·Agent·Tool 실행 결과가 아닙니다.",
        "",
        "| Case | 목적 | 예상 판정 | 예상 원인 | 정답 상태 | 실행 상태 |",
        "|---|---|---|---|---|---|",
    ]

    for answer in answers:
        expected = answer["expected"]

        rows.append(
            f"| {answer['case_id']} "
            f"| {answer['title']} "
            f"| {expected['decision'] or '미확정'} "
            f"| {expected['issue_code'] or '해당 없음'} "
            f"| {answer['oracle_status']} "
            "| NOT_RUN |"
        )

    rows.extend(
        [
            "",
            "## 사용 방법",
            "",
            "- 1번 담당자는 scenario.json의 phases를 읽고 "
            "case_data만 기존 Tool에 전달합니다.",
            "- expected와 answer.json은 정답이며, "
            "Agent/LLM/판정 함수의 입력으로 전달하지 않습니다.",
            "- QA-002는 영향범위 제외가 정답입니다. "
            "품질 PASS와 구분합니다.",
            "- QA-009는 검사성적서 Lot 불일치 시 HOLD로 판정하며, "
            "올바른 검사성적서 제출 후 재검증합니다.",
            "- QA-010은 문서 Revision 문제와 공차 초과가 동시에 있는 사례입니다. "
            "실제 결과가 HOLD여도 정답을 결과에 맞춰 바꾸지 않습니다.",
            "- evidence의 json_pointer는 같은 Case의 scenario.json 내부 경로입니다. "
            "PDF가 없으므로 페이지 번호를 만들지 않았습니다.",
            "- 실제 판정, 원인, 통과 여부와 실행시간은 "
            "1번의 실행 결과로 별도 기록합니다.",
        ]
    )

    files[OUTPUT / "answer_key.md"] = (
        "\n".join(rows) + "\n"
    )

    # 이미 수정된 자료가 있으면 덮어쓰지 않는다.
    for path, content in files.items():
        if path.exists():
            existing = path.read_text(
                encoding="utf-8"
            )
            if existing != content:
                raise FileExistsError(
                    f"기존 파일과 달라 덮어쓰지 않았습니다: {path}"
                )

    for path, content in files.items():
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not path.exists():
            with path.open(
                "x",
                encoding="utf-8",
            ) as stream:
                stream.write(content)

    print(
        "추가 Case 10개 생성 완료: "
        "정답 정의 10개 / 팀 판정 확인 필요 0개"
    )
    print(
        "자료 조건 점검 완료. "
        "Tool 실행 결과는 아직 NOT_RUN입니다."
    )
    print(
        f"정답표: {OUTPUT / 'answer_key.md'}"
    )
    print(
        "기존 테스트, Tool, DB 파일은 수정하지 않았습니다."
    )


if __name__ == "__main__":
    main()