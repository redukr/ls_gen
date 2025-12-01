import json
import os
from typing import List

from .models import CardModel, DeckModel


class JSONLoader:
    def __init__(self, deck_path):
        self.deck_path = deck_path
        self.deck_folder = os.path.dirname(deck_path)
        self.data = None

    def load(self) -> DeckModel:
        if not os.path.exists(self.deck_path):
            raise FileNotFoundError(f"JSON deck not found: {self.deck_path}")

        with open(self.deck_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        self.normalize()
        deck_name = os.path.splitext(os.path.basename(self.deck_path))[0]
        cards: List[CardModel] = [CardModel(index=i, payload=card) for i, card in enumerate(self.data["cards"])]

        return DeckModel(
            name=deck_name,
            path=self.deck_path,
            deck_color=self.data.get("deck_color", "#FFFFFF"),
            cards=cards,
            prompts=self.data.get("prompts", {}),
            metadata={k: v for k, v in self.data.items() if k not in {"cards", "deck_color", "prompts"}},
        )

    # ─────────────────────────────────────────────
    # Нормалізація карт
    # ─────────────────────────────────────────────
    def normalize(self):
        if "cards" not in self.data:
            raise ValueError("JSON deck не містить масиву 'cards'")

        deck_color = self.data.get("deck_color", "#FFFFFF")
        prompts = self.data.get("prompts", {})

        for card in self.data["cards"]:
            card["deck_color"] = deck_color
            card["prompt"] = self._get_prompt(prompts, card)

            # арт (опція)
            card["art_path"] = self._autodetect_art(card)

    # ─────────────────────────────────────────────
    # Пошук prompt'а для типу картки
    # ─────────────────────────────────────────────
    def _get_prompt(self, prompts, card):
        t = card.get("type", "")
        if t in prompts:
            try:
                return prompts[t].format(name=card["name"])
            except KeyError:
                return prompts[t]
        return ""

    # ─────────────────────────────────────────────
    # Автовизначення шляху до арту
    # /arts/<deck_name>/<card_name>.png
    # ─────────────────────────────────────────────
    def _autodetect_art(self, card):
        name = card["name"]
        sanitized = "".join(c for c in name if c.isalnum() or c in " _-").rstrip()

        arts_dir = os.path.join(self.deck_folder, "..", "arts")
        arts_dir = os.path.abspath(arts_dir)

        candidates = [
            os.path.join(arts_dir, f"{sanitized}.png"),
            os.path.join(arts_dir, f"{sanitized}.jpg"),
            os.path.join(arts_dir, f"{sanitized}.webp"),
        ]

        for c in candidates:
            if os.path.exists(c):
                return c

        return None
