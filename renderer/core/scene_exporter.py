"""Helper that reuses CardSceneView to export deck PNGs."""

from __future__ import annotations

import os
import re
from typing import Callable, Optional, Set

from PySide6.QtGui import QPixmap

from widgets.card_scene_view import CardSceneView

from .models import DeckModel


WINDOWS_FORBIDDEN = set('<>:"/\\|?*')


def slugify_card_name(name: str) -> str:
    """Return a filesystem-safe slug for the given card name."""

    if not name:
        return "card"

    slug = "".join("_" if ch in WINDOWS_FORBIDDEN else ch for ch in name)
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("._- ")
    return slug.lower() or "card"


class SceneExporter:
    def __init__(self, scene_view: CardSceneView):
        self.scene_view = scene_view

    def export_deck(
        self,
        deck: DeckModel,
        export_dir: str,
        frame_path: Optional[str] = None,
        progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> str:
        os.makedirs(export_dir, exist_ok=True)
        if frame_path:
            pixmap = QPixmap(frame_path)
            if not pixmap.isNull():
                self.scene_view.set_frame_pixmap(pixmap)
        used_paths: Set[str] = set()
        for idx, card in enumerate(deck.cards):
            self.scene_view.apply_card_data(card.payload, deck.deck_color)
            safe_name = slugify_card_name(card.name)
            suffix = None
            if hasattr(card, "index") and isinstance(card.index, int):
                suffix = f"{card.index + 1:03d}"
            else:
                suffix = f"{idx + 1:03d}"
            out_path = self._build_unique_path(export_dir, safe_name, suffix, used_paths)
            self.scene_view.export_to_png(out_path)
            if progress:
                progress(idx + 1, len(deck), out_path)
        return export_dir

    # ------------------------------------------------------------------
    def _build_unique_path(
        self,
        export_dir: str,
        safe_name: str,
        suffix: Optional[str],
        used_paths: Set[str],
    ) -> str:
        stem = safe_name
        if suffix:
            stem = f"{safe_name}-{suffix}"

        candidate = stem
        counter = 1
        path = os.path.join(export_dir, f"{candidate}.png")
        while path in used_paths or os.path.exists(path):
            candidate = f"{stem}-{counter}"
            path = os.path.join(export_dir, f"{candidate}.png")
            counter += 1
        used_paths.add(path)
        return path
