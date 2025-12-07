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
            data = json.load(f)

        # Accept multiple JSON layouts produced by the data editor:
        # 1) {"cards": [...], "meta": ...}
        # 2) {"id1": {...}, "id2": {...}}
        # 3) [...] (plain list)
        if isinstance(data, dict):
            if "cards" in data and isinstance(data["cards"], list):
                return data["cards"]
            if all(isinstance(v, dict) for v in data.values()):
                return list(data.values())
            return data

        if isinstance(data, list):
            return data

        # Unknown JSON shape – better to return an empty list than a raw scalar
        # that would not personalize prompts.
        return []

    if path.endswith(".csv"):
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    return []
