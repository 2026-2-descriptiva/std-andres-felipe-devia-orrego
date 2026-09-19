import csv
import json
import os


def convert_csv_2_json(csv_file):
    base_folder = os.path.dirname(os.path.dirname(csv_file))
    output_folder = os.path.join(base_folder, "temp")
    os.makedirs(output_folder, exist_ok=True)

    name = os.path.splitext(os.path.basename(csv_file))[0]
    json_file = os.path.join(output_folder, f"{name}.json")

    with open(csv_file, "r", encoding="utf-8") as f:
        data = list(csv.DictReader(f))

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
