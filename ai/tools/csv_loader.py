import csv
import json
import os
from typing import List


class _SafeDict(dict):
    """A dict that leaves missing placeholders untouched during formatting."""

    def __missing__(self, key):
        return "{" + key + "}"


def _format_prompt(prompts: dict, card: dict) -> str:
    """Pick and format a prompt template by card type."""

    card_type = card.get("type", "")
    if not prompts or card_type not in prompts:
        return ""

    template = prompts[card_type]
    try:
        return template.format_map(_SafeDict(**card))
    except Exception:
        return template


def _prepare_card(card: dict, prompts: dict | None, style_hint: str | None) -> dict:
    """Attach prompt/style data from the deck-level metadata if available."""

    card_copy = dict(card)

    prompt_value = _format_prompt(prompts or {}, card_copy)
    if prompt_value:
        card_copy.setdefault("prompt", prompt_value)

    if style_hint and not card_copy.get("style_hint"):
        card_copy["style_hint"] = style_hint

    return card_copy


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
            deck_style_hint = data.get("style_hint")
            deck_prompts = data.get("prompts") if isinstance(data.get("prompts"), dict) else {}

            if "cards" in data and isinstance(data["cards"], list):
                return [
                    _prepare_card(card, deck_prompts, deck_style_hint)
                    for card in data["cards"]
                ]

            if all(isinstance(v, dict) for v in data.values()):
                return [
                    _prepare_card(card, deck_prompts, deck_style_hint)
                    for card in data.values()
                ]
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
