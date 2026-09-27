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