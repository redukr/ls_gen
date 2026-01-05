from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from PIL import Image
from psd_tools import PSDImage


@dataclass
class PsdLayer:
    """Simple container that represents a PSD layer."""

    name: str
    visible: bool
    bbox: Tuple[int, int, int, int]
    image: Image.Image


class PsdImportResult:
    """Holds flattened PSD image and extracted layers."""

    def __init__(self, size: Tuple[int, int], composite: Image.Image, layers: List[PsdLayer]):
        self.size = size
        self.composite = composite
        self.layers = layers

    # -----------------------------------------------------
    def save_composite(self, path: os.PathLike[str] | str) -> str:
        path = str(path)
        self.composite.save(path)
        return path

    # -----------------------------------------------------
    def export_layers(self, output_dir: os.PathLike[str] | str, include_hidden: bool = False) -> List[dict]:
        """
        Export individual PSD layers as PNG.

        Returns metadata with name, path and bbox for each exported layer.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        exported: List[dict] = []
        used_names: set[str] = set()
        for layer in self.layers:
            if not include_hidden and not layer.visible:
                continue

            base_name = _slugify(layer.name or "layer")
            file_name = base_name
            counter = 1
            while file_name in used_names:
                file_name = f"{base_name}_{counter}"
                counter += 1
            used_names.add(file_name)

            file_path = output_path / f"{file_name}.png"
            layer.image.save(file_path)
            exported.append(
                {
                    "name": layer.name,
                    "path": str(file_path),
                    "bbox": layer.bbox,
                    "visible": layer.visible,
                }
            )
        return exported


class PsdImporter:
    """Import a PSD and provide a flattened image plus layer metadata."""

    def __init__(self, path: str):
        self.path = path

    # -----------------------------------------------------
    def load(self) -> PsdImportResult:
        if not self.path or not os.path.exists(self.path):
            raise FileNotFoundError(f"PSD file not found: {self.path}")

        psd = PSDImage.open(self.path)
        composite = psd.composite()
        if composite is None:
            raise ValueError("PSD file could not be composited")

        composite = composite.convert("RGBA")
        layers = self._extract_layers(psd)
        return PsdImportResult(psd.size, composite, layers)

    # -----------------------------------------------------
    def _extract_layers(self, psd: PSDImage) -> List[PsdLayer]:
        layers: List[PsdLayer] = []
        for layer in psd.descendants():
            if layer.is_group():
                continue

            image = layer.composite()
            if image is None:
                continue

            layers.append(
                PsdLayer(
                    name=layer.name or "Layer",
                    visible=layer.visible,
                    bbox=layer.bbox,
                    image=image.convert("RGBA"),
                )
            )
        return layers


# ---------------------------------------------------------
def _slugify(name: str) -> str:
    name = name.strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("._-")
    return name or "layer"
