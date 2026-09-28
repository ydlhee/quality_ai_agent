import csv


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


def trace_impact(file_path, part_id, old_revision, case_id):

    affected_lots = trace_affected_lots(
        file_path,
        part_id,
        old_revision
    )

    lots = []

    for lot_id in affected_lots:
        lots.append({
            "lot_id": lot_id,
            "part_id": part_id
        })

    return {
        "status": "success",
        "case_id": case_id,
        "result": {
            "affected_lots": lots
        },
        "evidence": [],
        "missing_items": []
    }