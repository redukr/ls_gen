import json
import csv

def load_params(path):
    """Завантажує CSV або JSON та повертає у вигляді dict або list."""
    if path.endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    elif path.endswith(".csv"):
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    else:
        return None
