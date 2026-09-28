import csv
from datetime import datetime


def trace_affected_lots(file_path, part_no, old_revision):

    affected_lots = []

    with open(file_path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if (
                row["part_no"] == part_no
                and row["revision"] == old_revision
            ):
                affected_lots.append(row["lot_id"])

    return affected_lots


def trace_impact(
    file_path,
    part_id,
    old_revision,
    case_id,
    effectivity=None
):

    affected_lots = []

    with open(file_path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:

            # Part가 다르면 영향대상 제외
            if row.get("part_no") != part_id:
                continue

            # 구 Revision을 사용한 Lot만 추적
            if row.get("revision") != old_revision:
                continue

            production_date = row.get("production_date", "")

            # Effectivity가 있는 경우 생산일 비교
            if effectivity is not None and production_date != "":

                effectivity_date = datetime.strptime(
                    effectivity,
                    "%Y-%m-%d"
                ).date()

                lot_date = datetime.strptime(
                    production_date,
                    "%Y-%m-%d"
                ).date()

                # 변경 적용일 이전에 생산된 Lot은 정상으로 보고 제외
                if lot_date < effectivity_date:
                    continue

            affected_lots.append({
                "lot_id": row["lot_id"],
                "part_id": part_id,
                "revision": row.get("revision", ""),
                "production_date": production_date
            })

    return {
        "status": "success",
        "case_id": case_id,
        "result": {
            "affected_lots": affected_lots
        },
        "evidence": [],
        "missing_items": []
    }