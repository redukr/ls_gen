"""Dataclasses that describe template, deck and card structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TemplateLayout:
    path: str
    data: Dict

    def clone(self) -> "TemplateLayout":
        import copy

        return TemplateLayout(path=self.path, data=copy.deepcopy(self.data))


@dataclass
class CardModel:
    index: int
    payload: Dict

    @property
    def name(self) -> str:
        return self.payload.get("name", f"Card {self.index + 1}")

    def get(self, key: str, default=None):
        return self.payload.get(key, default)

    def __getitem__(self, item):
        return self.payload[item]


@dataclass
class DeckModel:
    name: str
    path: str
    deck_color: str
    cards: List[CardModel] = field(default_factory=list)
    prompts: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)

    def card_at(self, index: int) -> Optional[CardModel]:
        if 0 <= index < len(self.cards):
            return self.cards[index]
        return None

    def __iter__(self):
        return iter(self.cards)

    def __len__(self) -> int:
        return len(self.cards)
