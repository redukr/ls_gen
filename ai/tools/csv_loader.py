import csv
import json
import os
from typing import List


def load_params(path) -> List[dict]:
    """Завантажує CSV або JSON та повертає у вигляді dict або list."""

    if not path:
        return []

    if not os.path.exists(path):
        return []

    if path.endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    if path.endswith(".csv"):
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    return []
