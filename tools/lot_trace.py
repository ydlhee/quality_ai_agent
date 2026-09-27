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