"""합의된 Revision/Heat 기준 반영 및 가상 테스트 자료 생성."""

import ast
import copy
import json
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent


HEAT_CHECK = '''expected_heat_no = requirements.get("expected_heat_no")
    if expected_heat_no:
        missing = [name for name, value in (
            ("소재성적서", material_heat_no),
            ("열처리성적서", heat_heat_no),
        ) if not value]

        mismatched = [name for name, value in (
            ("소재성적서", material_heat_no),
            ("열처리성적서", heat_heat_no),
        ) if value and value != expected_heat_no]

        if mismatched:
            return make_result(
                "HOLD",
                "HEAT_NO_MISMATCH",
                "기준 Heat No. 불일치: " + ", ".join(mismatched),
                expected_heat_no,
                {
                    "material": material_heat_no,
                    "heat_treatment": heat_heat_no,
                },
            )

        if missing:
            return make_result(
                "HOLD",
                "HEAT_NO_MISSING",
                "Heat No. 누락: " + ", ".join(missing),
                expected_heat_no,
                {
                    "material": material_heat_no,
                    "heat_treatment": heat_heat_no,
                },
            )

    elif (
        material_heat_no
        and heat_heat_no
        and material_heat_no != heat_heat_no
    ):
        return make_result(
            "HOLD",
            "HEAT_NO_MISMATCH",
            "성적서 간 Heat No. 불일치",
            material_heat_no,
            heat_heat_no,
        )'''


RUNNER = '''import json
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

        print(f"\\\\n===== {name} =====")

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
        f"\\\\n총 15개: PASS {success}, FAIL {15 - success}"
    )
    print(
        "가상 구조화 자료 기반 Tool 테스트입니다. "
        "Gmail/DB 통합 검증은 별도입니다."
    )

    return 0 if success == 15 else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''


def source_span(source, node, replacement):
    """선택한 코드 구간만 교체한다."""
    lines = source.splitlines(keepends=True)

    start = sum(
        map(len, lines[:node.lineno - 1])
    )
    end = sum(
        map(len, lines[:node.end_lineno - 1])
    )

    start += len(
        lines[node.lineno - 1]
        .encode()[:node.col_offset]
        .decode()
    )
    end += len(
        lines[node.end_lineno - 1]
        .encode()[:node.end_col_offset]
        .decode()
    )

    return source[:start] + replacement + source[end:]


def patch_tools():
    rules_path = (
        ROOT / "tools" / "quality_rules.py"
    )
    verify_path = (
        ROOT / "tools" / "quality_verify.py"
    )

    rules = rules_path.read_text(
        encoding="utf-8-sig"
    )
    verify = verify_path.read_text(
        encoding="utf-8-sig"
    )

    # 검사성적서 Revision 판정만 HOLD로 바꾼다.
    # 실제 Lot Revision의 REJECT는 유지한다.
    candidates = []

    for node in ast.walk(ast.parse(rules)):
        if not isinstance(node, ast.Call):
            continue

        if not isinstance(node.func, ast.Name):
            continue

        if node.func.id != "make_result":
            continue

        if len(node.args) < 3:
            continue

        matched = any(
            isinstance(item, ast.Constant)
            and isinstance(item.value, str)
            and "검사성적서 Revision 불일치" in item.value
            for item in ast.walk(node.args[2])
        )

        if matched:
            candidates.append(node)

    if len(candidates) != 1:
        raise ValueError(
            "문서 Revision 코드가 변경됐습니다. "
            "현재 파일 확인이 필요합니다."
        )

    rules = source_span(
        rules,
        candidates[0].args[0],
        '"HOLD"',
    )

    # 이미 수정된 파일이면 Heat 코드를 중복 삽입하지 않는다.
    marker = (
        'expected_heat_no = '
        'requirements.get("expected_heat_no")'
    )

    if marker not in rules:
        candidates = []

        for node in ast.walk(ast.parse(rules)):
            if not isinstance(node, ast.If):
                continue

            names = {
                item.id
                for item in ast.walk(node.test)
                if isinstance(item, ast.Name)
            }

            if names == {
                "material_heat_no",
                "heat_heat_no",
            }:
                candidates.append(node)

        if len(candidates) != 1:
            raise ValueError(
                "Heat 비교 코드가 변경됐습니다. "
                "현재 파일 확인이 필요합니다."
            )

        rules = source_span(
            rules,
            candidates[0],
            HEAT_CHECK,
        )

    # Case의 기준 Heat 번호를 Rule 입력에 전달한다.
    injection = (
        'requirements = {**requirements, '
        '"expected_heat_no": '
        'case_data.get("case", {}).get("expected_heat_no")}'
    )

    if injection not in verify:
        candidates = []

        for node in ast.walk(ast.parse(verify)):
            if not isinstance(node, ast.Assign):
                continue

            matched = any(
                isinstance(target, ast.Name)
                and target.id == "rule_result"
                for target in node.targets
            )

            if matched:
                candidates.append(node)

        if len(candidates) != 1:
            raise ValueError(
                "품질검증 코드가 변경됐습니다. "
                "현재 파일 확인이 필요합니다."
            )

        node = candidates[0]
        lines = verify.splitlines(keepends=True)

        lines.insert(
            node.lineno - 1,
            " " * node.col_offset + injection + "\n",
        )

        verify = "".join(lines)

    return {
        rules_path: rules,
        verify_path: verify,
    }


def baseline(index):
    """정상 조건을 갖춘 가상 Case를 만든다."""
    lot_no = f"LOT{index:03d}"
    part_no = "A1001"

    def doc(kind, name, data):
        return {
            "document_type": kind,
            "file_name": name,
            "document_stage": "INITIAL",
            "structured_data": data,
        }

    documents = []

    for revision, tolerance in (
        ("B", 0.2),
        ("C", 0.1),
    ):
        documents.append(
            doc(
                "DRAWING",
                f"rev_{revision.lower()}.json",
                {
                    "part_no": part_no,
                    "revision": revision,
                    "material": "AL7075",
                    "heat_treatment": "T6",
                    "characteristics": [
                        {
                            "nominal_mm": 20.0,
                            "tolerance_mm": tolerance,
                        }
                    ],
                },
            )
        )

    documents.append(
        doc(
            "INSPECTION_REPORT",
            "inspection.json",
            {
                "lot_no": lot_no,
                "revision": "C",
                "measured_mm": 20.05,
            },
        )
    )

    documents.append(
        doc(
            "MATERIAL_CERTIFICATE",
            "material.json",
            {
                "lot_no": lot_no,
                "material": "AL7075",
                "heat_no": "HEAT-100",
            },
        )
    )

    documents.append(
        doc(
            "HEAT_TREATMENT_CERTIFICATE",
            "heat.json",
            {
                "lot_no": lot_no,
                "heat_treatment": "T6",
                "heat_no": "HEAT-100",
            },
        )
    )

    return {
        "case": {
            "case_id": f"VAL-{index:03d}",
            "part_no": part_no,
            "drawing_revision": "C",
        },
        "lot": {
            "lot_no": lot_no,
            "part_no": part_no,
            "revision": "C",
            "production_date": "2026-09-20",
            "effectivity_date": "2026-09-15",
        },
        "documents": documents,
    }


def phase(
    name,
    data,
    decision,
    issue="NO_ISSUE",
    scope="IN_EFFECTIVITY_SCOPE",
):
    return {
        "name": name,
        "case_data": copy.deepcopy(data),
        "expected": {
            "decision": decision,
            "issue_code": issue,
            "scope": scope,
        },
    }


def create_scenarios():
    result = {}

    for index in range(1, 16):
        data = baseline(index)
        documents = data["documents"]

        decision = "PASS"
        issue = "NO_ISSUE"

        if index in (2, 10):
            # 측정값 누락
            documents[2]["structured_data"]["measured_mm"] = None
            decision = "HOLD"
            issue = "MEASUREMENT_MISSING"

        elif index == 3:
            # 공차 초과
            documents[2]["structured_data"]["measured_mm"] = 20.15
            decision = "REJECT"
            issue = "DIMENSION_OUT_OF_TOLERANCE"

        elif index == 4:
            # Lot은 C, 검사성적서만 B
            documents[2]["structured_data"]["revision"] = "B"
            decision = "HOLD"
            issue = "REVISION_MISMATCH"

        elif index == 5:
            # 요구 재질 변경, 소재성적서는 기존 재질
            documents[1]["structured_data"]["material"] = "AL2024"
            decision = "REJECT"
            issue = "MATERIAL_MISMATCH"

        elif index == 6:
            # 요구 열처리 변경, 성적서는 기존 조건
            documents[1]["structured_data"]["heat_treatment"] = "T73"
            decision = "REJECT"
            issue = "HEAT_TREATMENT_MISMATCH"

        elif index == 7:
            # 검사성적서 자체 누락
            del documents[2]
            decision = "HOLD"
            issue = "REQUIRED_DOCUMENT_MISSING"

        elif index in (8, 12, 13):
            documents[3]["structured_data"]["heat_no"] = "HEAT-999"

            # 12번은 기준 없이 문서끼리 비교한다.
            if index != 12:
                data["case"]["expected_heat_no"] = "HEAT-100"

            # 13번은 두 성적서가 서로 같지만 기준과 다르다.
            if index == 13:
                documents[4]["structured_data"]["heat_no"] = "HEAT-999"

            decision = "HOLD"
            issue = "HEAT_NO_MISMATCH"

        elif index == 11:
            # 실제 Lot Revision 불일치
            data["lot"]["revision"] = "B"
            decision = "REJECT"
            issue = "REVISION_MISMATCH"

        elif index == 14:
            # 기준은 있지만 성적서 Heat 번호 누락
            data["case"]["expected_heat_no"] = "HEAT-100"
            documents[4]["structured_data"]["heat_no"] = None
            decision = "HOLD"
            issue = "HEAT_NO_MISSING"

        elif index == 15:
            # 기준 Heat 번호와 두 성적서 모두 일치
            data["case"]["expected_heat_no"] = "HEAT-100"

        phases = [
            phase(
                "initial",
                data,
                decision,
                issue,
            )
        ]

        if index == 9:
            # 적용 이전 Lot과 적용 이후 Lot을 각각 검증한다.
            old_data = baseline(index)

            old_data["lot"].update(
                lot_no="LOT009A",
                revision="B",
                production_date="2026-09-10",
            )
            old_data["documents"] = (
                old_data["documents"][:2]
            )

            data["lot"]["lot_no"] = "LOT009B"

            for item in data["documents"][2:]:
                item["structured_data"]["lot_no"] = "LOT009B"

            phases = [
                phase(
                    "before_effectivity",
                    old_data,
                    "EXCLUDED",
                    scope="BEFORE_EFFECTIVITY",
                ),
                phase(
                    "after_effectivity",
                    data,
                    "PASS",
                ),
            ]

        if index == 10:
            # 기존 Case에 보완 검사성적서를 추가한다.
            corrected = copy.deepcopy(
                documents[2]
            )
            corrected["file_name"] = (
                "inspection_corrected.json"
            )
            corrected["document_stage"] = "SUPPLEMENTAL"
            corrected["structured_data"]["measured_mm"] = 20.05

            data["documents"].append(corrected)

            phases.append(
                phase(
                    "revalidation",
                    data,
                    "PASS",
                )
            )

        path = (
            ROOT
            / "data"
            / "validation_cases_v2"
            / f"VAL-{index:03d}"
            / "scenario.json"
        )

        result[path] = json.dumps(
            {
                "synthetic_fixture": True,
                "phases": phases,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n"

    return result


def main():
    # 모든 수정 내용을 먼저 준비한다.
    # 기존 코드가 예상 구조와 다르면 저장 전에 중단한다.
    writes = patch_tools()

    writes[
        ROOT / "test_validation_cases.py"
    ] = RUNNER

    writes.update(
        create_scenarios()
    )

    # 저장 전에 Python 문법을 확인한다.
    for path, source in writes.items():
        if path.suffix == ".py":
            compile(
                source,
                str(path),
                "exec",
            )

    backup = Path(
        tempfile.mkdtemp(
            prefix="aerochange_validation_"
        )
    )

    originals = {
        path: (
            path.read_bytes()
            if path.exists()
            else None
        )
        for path in writes
    }

    # 기존 파일을 백업한다.
    for path, content in originals.items():
        if content is None:
            continue

        saved = (
            backup / path.relative_to(ROOT)
        )
        saved.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        saved.write_bytes(content)

    try:
        for path, source in writes.items():
            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            path.write_text(
                source,
                encoding="utf-8",
            )

    except Exception:
        # 저장 실패 시 변경 전 내용으로 복구한다.
        for path, content in originals.items():
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(content)
        raise

    print(f"기존 파일 백업: {backup}")
    print(
        "Tool 2개 수정, v2 테스트 자료 15개 생성, "
        "테스트 파일 교체 완료"
    )
    print(
        "기존 data/validation_cases와 DB는 "
        "변경하지 않았습니다."
    )
    print(
        "다음 실행: "
        "python .\\test_validation_cases.py"
    )


if __name__ == "__main__":
    main()