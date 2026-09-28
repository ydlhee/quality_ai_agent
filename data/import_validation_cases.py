import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "data" / "validation_cases"

SOURCE_BRANCH = "origin/seon-dev"


def git_read_text(path):
    result = subprocess.run(
        [
            "git",
            "show",
            f"{SOURCE_BRANCH}:{path}",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    if result.returncode != 0:
        raise FileNotFoundError(
            f"seon-dev에서 파일을 찾을 수 없습니다: {path}"
        )

    return result.stdout


def git_list_files(case_id):
    case_path = f"data/test_cases/{case_id}"

    result = subprocess.run(
        [
            "git",
            "ls-tree",
            "-r",
            "--name-only",
            SOURCE_BRANCH,
            case_path,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"{case_id} 파일 목록 조회 실패"
        )

    return [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]


def migrate_case(number):
    source_case_id = f"CASE-{number:03d}"
    validation_id = f"VAL-{number:03d}"

    output_case_dir = OUTPUT_DIR / validation_id
    output_case_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    files = git_list_files(source_case_id)

    if not files:
        raise FileNotFoundError(
            f"{source_case_id} 데이터가 없습니다."
        )

    for source_path in files:
        file_name = Path(source_path).name

        content = git_read_text(source_path)

        # case.json 내부 ID도 VAL 형식으로 변경
        if file_name == "case.json":
            case_data = json.loads(content)

            case_data["case_id"] = validation_id
            case_data["source_case_id"] = source_case_id
            case_data["dataset_type"] = "VALIDATION"

            content = json.dumps(
                case_data,
                ensure_ascii=False,
                indent=2,
            )

        output_path = output_case_dir / file_name

        output_path.write_text(
            content,
            encoding="utf-8",
        )

    print(
        f"{source_case_id} → {validation_id} 변환 완료 "
        f"({len(files)}개 파일)"
    )


def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for number in range(1, 11):
        migrate_case(number)

    print()
    print("Validation Case 변환 완료")
    print(f"저장 위치: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()