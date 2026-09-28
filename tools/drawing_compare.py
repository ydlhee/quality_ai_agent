import json


def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def compare_revision(old_file, new_file):

    old_data = load_json(old_file)
    new_data = load_json(new_file)

    changes = []

    for key in new_data:

        old_value = old_data.get(key)
        new_value = new_data.get(key)

        if old_value != new_value:
            changes.append({
                "item": key,
                "old": old_value,
                "new": new_value
            })

    return changes


def analyze_design_change(old_file, new_file, case_id):
    changes = compare_revision(old_file, new_file)

    return {
        "status": "success",
        "case_id": case_id,
        "result": {
            "changes": changes
        },
        "evidence": [],
        "missing_items": []
    }