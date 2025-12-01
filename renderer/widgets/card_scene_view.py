"""Interactive QGraphicsView-based template editor and renderer."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, QSizeF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
)

APP_DIR = Path(__file__).resolve().parent.parent
DEFAULT_LAYOUT = APP_DIR / "editor" / "template_layout.json"


def resource_path(*paths: str) -> str:
    return str(APP_DIR.joinpath(*paths))


class _CardItemBase:
    """Mixin that injects shared behaviour into interactive scene items."""

    def __init__(self, scene_view: "CardSceneView", item_id: str, config: dict) -> None:
        self.scene_view = scene_view
        self.item_id = item_id
        self.config = config
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, not config.get("locked", False))

    # ------------------------------------------------------------------
    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):  # type: ignore[override]
        if change == QGraphicsItem.ItemSelectedChange and bool(value):
            self.scene_view._handle_item_selected(self)
        if change == QGraphicsItem.ItemPositionChange:
            return self.scene_view._handle_item_moved(self, value)
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.scene_view._emit_item_update(self.item_id)
        return super().itemChange(change, value)  # type: ignore[misc]


class CardTextItem(_CardItemBase, QGraphicsTextItem):
    def __init__(self, scene_view: "CardSceneView", item_id: str, config: dict):
        QGraphicsTextItem.__init__(self, config.get("text", ""))
        _CardItemBase.__init__(self, scene_view, item_id, config)
        font_cfg = config.get("font", {})
        font = QFont(font_cfg.get("family", "Arial"), font_cfg.get("size", 20))
        font.setBold(font_cfg.get("bold", False))
        font.setItalic(font_cfg.get("italic", False))
        font.setUnderline(font_cfg.get("underline", False))
        self.setFont(font)
        color = QColor(config.get("color", "#FFFFFF"))
        self.setDefaultTextColor(color)
        text_width = config.get("text_width")
        if text_width:
            self.setTextWidth(text_width)
        self.setPos(config.get("pos", {}).get("x", 0), config.get("pos", {}).get("y", 0))
        self.setZValue(config.get("z", 5))
        self.setOpacity(config.get("opacity", 1.0))
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        if config.get("shadow"):
            self._apply_shadow(config["shadow"])

    # ------------------------------------------------------------------
    def _apply_shadow(self, cfg: dict) -> None:
        effect = QGraphicsDropShadowEffect()
        effect.setColor(QColor(cfg.get("color", "#000000")))
        offset = cfg.get("offset", [0, 0])
        effect.setOffset(offset[0], offset[1])
        effect.setBlurRadius(cfg.get("blur", 0))
        self.setGraphicsEffect(effect)


class CardPixmapItem(_CardItemBase, QGraphicsPixmapItem):
    def __init__(self, scene_view: "CardSceneView", item_id: str, config: dict):
        pixmap = QPixmap(config.get("asset", "")) if config.get("asset") else QPixmap()
        QGraphicsPixmapItem.__init__(self, pixmap)
        _CardItemBase.__init__(self, scene_view, item_id, config)
        self.setTransformationMode(Qt.SmoothTransformation)
        self.setPos(config.get("pos", {}).get("x", 0), config.get("pos", {}).get("y", 0))
        self.setZValue(config.get("z", 2))
        self.setOpacity(config.get("opacity", 1.0))


class CardRectItem(_CardItemBase, QGraphicsRectItem):
    def __init__(self, scene_view: "CardSceneView", item_id: str, config: dict):
        rect_cfg = config.get("size", {})
        rect = QRectF(0, 0, rect_cfg.get("w", 100), rect_cfg.get("h", 100))
        QGraphicsRectItem.__init__(self, rect)
        _CardItemBase.__init__(self, scene_view, item_id, config)
        pen_cfg = config.get("pen", {"color": "#FFFFFF", "width": 1})
        pen = QPen(QColor(pen_cfg.get("color", "#FFFFFF")), pen_cfg.get("width", 1))
        self.setPen(pen)
        brush_cfg = config.get("brush")
        if brush_cfg:
            self.setBrush(QColor(brush_cfg.get("color", "#FFFFFF")))
        self.setPos(config.get("pos", {}).get("x", 0), config.get("pos", {}).get("y", 0))
        self.setZValue(config.get("z", 1))
        self.setOpacity(config.get("opacity", 1.0))


class CardSceneView(QGraphicsView):
    """Scene-based template editor with layout persistence."""

    selectionChanged = Signal(str)
    itemUpdated = Signal(str, dict)
    layoutLoaded = Signal(dict)

    itemSelected = Signal(object)

    def __init__(self, template_path: Optional[str] = None, parent=None):
        super().__init__(parent)

        self.layout_path = template_path or str(DEFAULT_LAYOUT)
        self.layout: Dict[str, dict] = {}
        self.scene_items: Dict[str, QGraphicsItem] = {}
        self.template_locked = False
        self.edit_mode = "template"
        self._card_mode_snapshot: Optional[dict] = None
        self._deck_color = QColor("#FFFFFF")

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self.card_size = QSizeF(744, 1038)
        self.dpi = 300
        self.grid_size = 25
        self.snap_size = 5

        self._background_color = QColor(26, 26, 26)
        self._card_rect_item = QGraphicsRectItem(0, 0, self.card_size.width(), self.card_size.height())
        self._card_rect_item.setPen(QPen(QColor(240, 240, 240), 2))
        self._card_rect_item.setBrush(Qt.NoBrush)
        self._card_rect_item.setZValue(-5)
        self._scene.addItem(self._card_rect_item)

        self._frame_item = QGraphicsPixmapItem()
        self._frame_item.setZValue(-2)
        self._frame_item.setTransformationMode(Qt.SmoothTransformation)
        self._scene.addItem(self._frame_item)

        self._art_item_id = "artwork"
        self._default_art_pixmap = QPixmap(520, 320)
        self._default_art_pixmap.fill(QColor(45, 60, 75))

        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setDragMode(QGraphicsView.RubberBandDrag)

        self._scene.setSceneRect(-400, -400, 1600, 2400)
        self._fit_scheduled = True

        self._scene.selectionChanged.connect(self._on_selection_changed)

        if template_path:
            self.load_template(template_path)

    # ------------------------------------------------------------------
    def _emit_selected_item(self):
        selected = self._scene.selectedItems()
        item = selected[0] if selected else None
        self.itemSelected.emit(item)

    # ------------------------------------------------------------------
    def _on_selection_changed(self):
        self._emit_selected_item()

    # ------------------------------------------------------------------
    def apply_card_data(self, card: dict, deck_color: str):
        """Populate scene items using card data from JSON."""
        if not card:
        if not os.path.exists(self.layout_path):
            self._ensure_default_layout()
        self.load_template(self.layout_path)

    # ------------------------------------------------------------------
    def _ensure_default_layout(self):
        DEFAULT_LAYOUT.parent.mkdir(parents=True, exist_ok=True)
        layout = {
            "meta": {
                "width": 744,
                "height": 1038,
                "dpi": 300,
                "background": "#1c1c1c",
                "grid": 25,
                "snap": 5,
            },
            "items": {
                "artwork": {
                    "type": "image",
                    "pos": {"x": 112, "y": 160},
                    "size": {"w": 520, "h": 320},
                    "z": 1,
                    "locked": False,
                    "opacity": 1.0,
                },
                "title": {
                    "type": "text",
                    "text": "Назва картки",
                    "pos": {"x": 60, "y": 40},
                    "font": {"family": "Arial", "size": 30, "bold": True},
                    "color": "#FFFFFF",
                    "text_width": 500,
                    "z": 5,
                },
                "type": {
                    "type": "text",
                    "text": "UNIT",
                    "pos": {"x": 60, "y": 90},
                    "font": {"family": "Arial", "size": 18, "bold": False},
                    "color": "#F7D56E",
                    "z": 5,
                },
                "description": {
                    "type": "text",
                    "text": "Опис здібностей та ефектів...",
                    "pos": {"x": 60, "y": 520},
                    "font": {"family": "Arial", "size": 18},
                    "color": "#FFFFFF",
                    "text_width": 520,
                    "z": 5,
                },
            },
        }
        with open(DEFAULT_LAYOUT, "w", encoding="utf-8") as fh:
            json.dump(layout, fh, indent=4, ensure_ascii=False)

    # ------------------------------------------------------------------
    def load_template(self, template_path: str):
        if not template_path:
            return
        self.layout_path = template_path
        with open(template_path, "r", encoding="utf-8") as fh:
            self.layout = json.load(fh)
        self._apply_layout_meta()
        self._build_scene_items()
        self.layoutLoaded.emit(copy.deepcopy(self.layout))

    # ------------------------------------------------------------------
    def save_layout(self, output_path: Optional[str] = None):
        if self.edit_mode != "template":
            return
        path = output_path or self.layout_path
        self._sync_layout_from_items()
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.layout, fh, indent=4, ensure_ascii=False)

    # ------------------------------------------------------------------
    def _apply_layout_meta(self):
        meta = self.layout.get("meta", {})
        self.card_size = QSizeF(meta.get("width", 744), meta.get("height", 1038))
        self.dpi = meta.get("dpi", 300)
        self.grid_size = meta.get("grid", 25)
        self.snap_size = meta.get("snap", 5)
        self._background_color = QColor(meta.get("background", "#1a1a1a"))
        self._card_rect_item.setRect(QRectF(0, 0, self.card_size.width(), self.card_size.height()))
        self._scene.setSceneRect(self._card_rect_item.rect().adjusted(-250, -250, 250, 250))
        self.fit_card_to_view()
        self._apply_relative_positions()

    # ------------------------------------------------------------------
    def _build_scene_items(self):
        for item in list(self.scene_items.values()):
            self._scene.removeItem(item)
        self.scene_items.clear()
        items = self.layout.get("items", {})
        for item_id, cfg in items.items():
            created = self._create_item(item_id, cfg)
            if created:
                self.scene_items[item_id] = created
                self._scene.addItem(created)
        art_item = self.scene_items.get(self._art_item_id)
        if isinstance(art_item, QGraphicsPixmapItem) and art_item.pixmap().isNull():
            self._set_image(self._art_item_id, self._default_art_pixmap, persist=False)
        self._apply_relative_positions()
        self.fit_card_to_view()

    # ------------------------------------------------------------------
    def _create_item(self, item_id: str, cfg: dict) -> Optional[QGraphicsItem]:
        item_type = cfg.get("type", "text")
        if item_type == "text":
            return CardTextItem(self, item_id, cfg)
        if item_type in {"image", "pixmap", "icon"}:
            item = CardPixmapItem(self, item_id, cfg)
            size = cfg.get("size")
            if size and not item.pixmap().isNull():
                scaled = item.pixmap().scaled(
                    size.get("w", item.pixmap().width()),
                    size.get("h", item.pixmap().height()),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                item.setPixmap(scaled)
            return item
        if item_type in {"rect", "decor"}:
            return CardRectItem(self, item_id, cfg)
        return None

    # ------------------------------------------------------------------
    def _apply_relative_positions(self):
        for item_id, item in self.scene_items.items():
            cfg = self.layout.get("items", {}).get(item_id, {})
            bindings = cfg.get("bindings", {})
            if not bindings.get("relative"):
                continue
            anchor = bindings.get("anchor", {})
            rel_x = anchor.get("x")
            rel_y = anchor.get("y")
            if rel_x is None or rel_y is None:
                pos = cfg.get("pos", {})
                rel_x = pos.get("x", 0) / max(1.0, self.card_size.width())
                rel_y = pos.get("y", 0) / max(1.0, self.card_size.height())
            new_x = rel_x * self.card_size.width()
            new_y = rel_y * self.card_size.height()
            item.setPos(new_x, new_y)
            cfg.setdefault("pos", {})
            cfg["pos"].update({"x": new_x, "y": new_y})

    # ------------------------------------------------------------------
    def _sync_layout_from_items(self):
        for item_id, item in self.scene_items.items():
            cfg = self.layout.setdefault("items", {}).setdefault(item_id, {})
            cfg["type"] = cfg.get("type", self._infer_type(item))
            pos = cfg.setdefault("pos", {})
            pos["x"] = float(item.pos().x())
            pos["y"] = float(item.pos().y())
            cfg["z"] = item.zValue()
            cfg["opacity"] = item.opacity()
            if isinstance(item, QGraphicsTextItem):
                cfg["text"] = item.toPlainText()
                cfg.setdefault("font", {})["family"] = item.font().family()
                cfg["font"]["size"] = item.font().pointSize()
                cfg["font"]["bold"] = item.font().bold()
                cfg["font"]["italic"] = item.font().italic()
                cfg["font"]["underline"] = item.font().underline()
                if item.textWidth() > 0:
                    cfg["text_width"] = item.textWidth()
                cfg["color"] = item.defaultTextColor().name(QColor.HexArgb)
            if isinstance(item, QGraphicsPixmapItem):
                cfg["asset"] = cfg.get("asset")
                size = cfg.setdefault("size", {})
                if not item.pixmap().isNull():
                    size["w"] = item.pixmap().width()
                    size["h"] = item.pixmap().height()
            if isinstance(item, QGraphicsRectItem):
                size = cfg.setdefault("size", {})
                rect = item.rect()
                size["w"] = rect.width()
                size["h"] = rect.height()
                pen = item.pen()
                cfg.setdefault("pen", {})["color"] = pen.color().name(QColor.HexArgb)
                cfg["pen"]["width"] = pen.widthF()
                brush = item.brush()
                if brush.style() != Qt.NoBrush:
                    cfg.setdefault("brush", {})["color"] = brush.color().name(QColor.HexArgb)

    # ------------------------------------------------------------------
    def _infer_type(self, item: QGraphicsItem) -> str:
        if isinstance(item, QGraphicsTextItem):
            return "text"
        if isinstance(item, QGraphicsRectItem):
            return "rect"
        return "image"

    # ------------------------------------------------------------------
    def set_frame_pixmap(self, pixmap: QPixmap):
        if pixmap.isNull():
            return
        self._frame_item.setPixmap(pixmap)
        self._frame_item.setPos(0, 0)
        self._frame_item.setScale(1.0)
        self._frame_item.setOpacity(1.0)
        self._frame_item.setTransformationMode(Qt.SmoothTransformation)
        self._scene.update()

    # ------------------------------------------------------------------
    def set_template_locked(self, locked: bool):
        self.template_locked = locked
        for item in self.scene_items.values():
            cfg = getattr(item, "config", {})
            allow_move = not (locked or cfg.get("locked", False))
            item.setFlag(QGraphicsItem.ItemIsMovable, allow_move)

    # ------------------------------------------------------------------
    def set_edit_mode(self, mode: str):
        if mode == self.edit_mode:
            return
        if mode == "card":
            self._card_mode_snapshot = copy.deepcopy(self.layout)
        else:
            if self._card_mode_snapshot:
                self.layout = self._card_mode_snapshot
                self._card_mode_snapshot = None
                self._apply_layout_meta()
                self._build_scene_items()
        self.edit_mode = mode

    # ------------------------------------------------------------------
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self._emit_selected_item()

    # ------------------------------------------------------------------
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self._emit_selected_item()

    # ------------------------------------------------------------------
    def drawBackground(self, painter: QPainter, rect: QRectF):
        painter.fillRect(rect, QColor(26, 26, 26))

        grid_size = 50
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)
    def _handle_item_selected(self, item: QGraphicsItem):
        item_id = self._lookup_item_id(item)
        if item_id:
            self.selectionChanged.emit(item_id)

    # ------------------------------------------------------------------
    def _lookup_item_id(self, item: QGraphicsItem) -> Optional[str]:
        for item_id, scene_item in self.scene_items.items():
            if scene_item is item:
                return item_id
        return None

    # ------------------------------------------------------------------
    def _handle_item_moved(self, item: QGraphicsItem, value):
        if self.template_locked:
            return item.pos()
        new_pos = QPointF(value)
        rect = self._card_rect_item.rect()
        bounds = item.mapRectToParent(item.boundingRect())
        width = bounds.width()
        height = bounds.height()
        min_x = rect.left()
        min_y = rect.top()
        max_x = rect.right() - width
        max_y = rect.bottom() - height
        x = max(min_x, min(new_pos.x(), max_x))
        y = max(min_y, min(new_pos.y(), max_y))
        if self.snap_size > 0:
            x = round(x / self.snap_size) * self.snap_size
            y = round(y / self.snap_size) * self.snap_size
        cfg = self.layout.get("items", {}).get(self._lookup_item_id(item) or "", {})
        bindings = cfg.get("bindings", {})
        if bindings.get("lock_x"):
            x = item.pos().x()
        if bindings.get("lock_y"):
            y = item.pos().y()
        return QPointF(x, y)

    # ------------------------------------------------------------------
    def _emit_item_update(self, item_id: str):
        cfg = self.get_item_config(item_id)
        if self.edit_mode == "template":
            self.layout.setdefault("items", {})[item_id] = copy.deepcopy(cfg)
        self.itemUpdated.emit(item_id, cfg)

    # ------------------------------------------------------------------
    def apply_card_data(self, card: dict, deck_color: str):
        if not card:
            return

        if not self._preview_item:
            self._preview_item = QGraphicsPixmapItem(pixmap)
            self._preview_item.setTransformationMode(Qt.SmoothTransformation)
            self._preview_item.setZValue(20)
            self._scene.addItem(self._preview_item)
        self._deck_color = QColor(deck_color) if QColor.isValidColor(deck_color) else QColor("#FFFFFF")
        # Textual content
        self._set_text("title", card.get("name", ""), persist=False)
        self._set_text("type", card.get("type", "").upper(), persist=False)
        desc = card.get("description") or card.get("text") or card.get("effect", "")
        self._set_text("description", desc, persist=False)
        stats = {
            "atk": card.get("atk", "-"),
            "def": card.get("def", "-"),
            "stb": card.get("stb", "-"),
            "init": card.get("init", "-"),
            "rng": card.get("rng", "-"),
            "move": card.get("move", "-"),
        }
        for key, value in stats.items():
            label = key.upper()
            self._set_text(f"stat_{key}", f"{label} {value}", persist=False)
        cost = card.get("cost")
        if cost is not None:
            self._set_text("cost", str(cost), persist=False)
        cost_type = card.get("cost_type")
        if cost_type:
            self._set_text("cost_type", cost_type, persist=False)
        # Artwork
        art_path = card.get("art_path")
        if art_path and os.path.exists(art_path):
            pix = QPixmap(art_path)
            self._set_image(self._art_item_id, pix, persist=False)
        else:
            self._set_image(self._art_item_id, self._default_art_pixmap, persist=False)
        self.set_deck_color(deck_color)

    # ------------------------------------------------------------------
    def _set_text(self, item_id: str, text: str, *, persist: bool = True):
        item = self.scene_items.get(item_id)
        if isinstance(item, QGraphicsTextItem):
            item.setPlainText(text)
            if persist and self.edit_mode == "template":
                cfg = self.layout.setdefault("items", {}).setdefault(item_id, {})
                cfg["text"] = text

    # ------------------------------------------------------------------
    def _set_image(self, item_id: str, pixmap: QPixmap, *, persist: bool = True):
        item = self.scene_items.get(item_id)
        if isinstance(item, QGraphicsPixmapItem) and not pixmap.isNull():
            size = self.layout.get("items", {}).get(item_id, {}).get("size")
            if size:
                pixmap = pixmap.scaled(
                    size.get("w", pixmap.width()),
                    size.get("h", pixmap.height()),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            item.setPixmap(pixmap)
            if persist and self.edit_mode == "template":
                cfg = self.layout.setdefault("items", {}).setdefault(item_id, {})
                cfg["asset"] = cfg.get("asset")

    # ------------------------------------------------------------------
    def set_deck_color(self, color_hex: str):
        color = QColor(color_hex) if QColor.isValidColor(color_hex) else QColor("white")
        pen = self._card_rect_item.pen()
        pen.setColor(color)
        self._card_rect_item.setPen(pen)

    # ------------------------------------------------------------------
    def export_to_png(self, path: str):
        if not path:
            return
        width = int(self.card_size.width())
        height = int(self.card_size.height())
        image = QImage(width, height, QImage.Format_ARGB32)
        image.setDotsPerMeterX(int(self.dpi / 25.4 * 1000))
        image.setDotsPerMeterY(int(self.dpi / 25.4 * 1000))
        image.fill(Qt.transparent)
        painter = QPainter(image)
        self._scene.render(painter, QRectF(0, 0, width, height), self._card_rect_item.rect())
        painter.end()
        image.save(path, "PNG")

    # ------------------------------------------------------------------
    def drawBackground(self, painter: QPainter, rect: QRectF):  # type: ignore[override]
        painter.fillRect(rect, self._background_color)
        grid = self.grid_size
        if grid <= 0:
            return
        pen = QPen(QColor(35, 35, 35))
        left = int(rect.left()) - (int(rect.left()) % grid)
        top = int(rect.top()) - (int(rect.top()) % grid)
        for x in range(left, int(rect.right()), grid):
            painter.setPen(pen)
            painter.drawLine(x, rect.top(), x, rect.bottom())
        for y in range(top, int(rect.bottom()), grid):
            painter.setPen(pen)
            painter.drawLine(rect.left(), y, rect.right(), y)

    # ------------------------------------------------------------------
    def resizeEvent(self, event):  # type: ignore[override]
        super().resizeEvent(event)
        if self._fit_scheduled:
            self.fit_card_to_view()
            self._fit_scheduled = False

    # ------------------------------------------------------------------
    def wheelEvent(self, event):  # type: ignore[override]
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 0.87
            self.scale(factor, factor)
            event.accept()
            return
        super().wheelEvent(event)

    # ------------------------------------------------------------------
    def fit_card_to_view(self):
        self.fitInView(self._card_rect_item, Qt.KeepAspectRatio)

    # ------------------------------------------------------------------
    def set_background_color(self, color: QColor):
        self._background_color = color
        self.layout.setdefault("meta", {})["background"] = color.name(QColor.HexArgb)
        self.viewport().update()

    # ------------------------------------------------------------------
    def update_text_width(self, item_id: str, width: float):
        item = self.scene_items.get(item_id)
        if isinstance(item, QGraphicsTextItem):
            item.setTextWidth(width)
            if self.edit_mode == "template":
                cfg = self.layout.setdefault("items", {}).setdefault(item_id, {})
                cfg["text_width"] = width

    # ------------------------------------------------------------------
    def update_font(self, item_id: str, font: QFont):
        item = self.scene_items.get(item_id)
        if isinstance(item, QGraphicsTextItem):
            item.setFont(font)
            if self.edit_mode == "template":
                cfg = self.layout.setdefault("items", {}).setdefault(item_id, {})
                cfg.setdefault("font", {})
                cfg["font"].update(
                    {
                        "family": font.family(),
                        "size": font.pointSize(),
                        "bold": font.bold(),
                        "italic": font.italic(),
                        "underline": font.underline(),
                    }
                )

    # ------------------------------------------------------------------
    def update_text_color(self, item_id: str, color: QColor):
        item = self.scene_items.get(item_id)
        if isinstance(item, QGraphicsTextItem):
            item.setDefaultTextColor(color)
            if self.edit_mode == "template":
                cfg = self.layout.setdefault("items", {}).setdefault(item_id, {})
                cfg["color"] = color.name(QColor.HexArgb)

    # ------------------------------------------------------------------
    def update_item_opacity(self, item_id: str, opacity: float):
        item = self.scene_items.get(item_id)
        if item:
            item.setOpacity(opacity)
            if self.edit_mode == "template":
                cfg = self.layout.setdefault("items", {}).setdefault(item_id, {})
                cfg["opacity"] = opacity

    # ------------------------------------------------------------------
    def update_item_size(self, item_id: str, size: Tuple[float, float]):
        item = self.scene_items.get(item_id)
        if isinstance(item, QGraphicsRectItem):
            rect = QRectF(0, 0, size[0], size[1])
            item.setRect(rect)
        if isinstance(item, QGraphicsPixmapItem) and not item.pixmap().isNull():
            scaled = item.pixmap().scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
            item.setPixmap(scaled)
        if self.edit_mode == "template":
            cfg = self.layout.setdefault("items", {}).setdefault(item_id, {})
            cfg.setdefault("size", {})
            cfg["size"].update({"w": size[0], "h": size[1]})

    # ------------------------------------------------------------------
    def update_item_position(self, item_id: str, pos: Tuple[float, float]):
        item = self.scene_items.get(item_id)
        if not item:
            return
        item.setPos(pos[0], pos[1])
        if self.edit_mode == "template":
            cfg = self.layout.setdefault("items", {}).setdefault(item_id, {})
            cfg.setdefault("pos", {})
            cfg["pos"].update({"x": pos[0], "y": pos[1]})
            bindings = cfg.get("bindings", {})
            if bindings.get("relative"):
                anchor = bindings.setdefault("anchor", {})
                anchor["x"] = pos[0] / max(1.0, self.card_size.width())
                anchor["y"] = pos[1] / max(1.0, self.card_size.height())

    # ------------------------------------------------------------------
    def apply_outline(self, item_id: str, color: QColor, width: float):
        item = self.scene_items.get(item_id)
        if not isinstance(item, QGraphicsTextItem):
            return
        effect = QGraphicsDropShadowEffect()
        effect.setOffset(0, 0)
        effect.setBlurRadius(max(0.0, width * 2))
        effect.setColor(color)
        item.setGraphicsEffect(effect)
        if self.edit_mode == "template":
            cfg = self.layout.setdefault("items", {}).setdefault(item_id, {})
            cfg.setdefault("shadow", {})
            cfg["shadow"].update({"color": color.name(QColor.HexArgb), "blur": max(0.0, width * 2), "offset": [0, 0]})

    # ------------------------------------------------------------------
    def change_icon_source(self, item_id: str, asset_path: str):
        item = self.scene_items.get(item_id)
        if not isinstance(item, QGraphicsPixmapItem):
            return
        pix = QPixmap(asset_path)
        if pix.isNull():
            return
        size = self.layout.get("items", {}).get(item_id, {}).get("size")
        if size:
            pix = pix.scaled(size.get("w", pix.width()), size.get("h", pix.height()), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        item.setPixmap(pix)
        if self.edit_mode == "template":
            cfg = self.layout.setdefault("items", {}).setdefault(item_id, {})
            cfg["asset"] = asset_path

    # ------------------------------------------------------------------
    def get_item_config(self, item_id: str) -> dict:
        cfg = copy.deepcopy(self.layout.get("items", {}).get(item_id, {}))
        item = self.scene_items.get(item_id)
        if item:
            cfg.setdefault("pos", {})
            cfg["pos"].update({"x": item.pos().x(), "y": item.pos().y()})
            cfg["z"] = item.zValue()
            cfg["opacity"] = item.opacity()
            if isinstance(item, QGraphicsTextItem):
                cfg["text"] = item.toPlainText()
                cfg.setdefault("font", {})
                cfg["font"].update(
                    {
                        "family": item.font().family(),
                        "size": item.font().pointSize(),
                        "bold": item.font().bold(),
                        "italic": item.font().italic(),
                        "underline": item.font().underline(),
                    }
                )
                cfg["color"] = item.defaultTextColor().name(QColor.HexArgb)
                if item.textWidth() > 0:
                    cfg["text_width"] = item.textWidth()
            if isinstance(item, QGraphicsPixmapItem) and not item.pixmap().isNull():
                cfg.setdefault("size", {})
                cfg["size"].update({"w": item.pixmap().width(), "h": item.pixmap().height()})
            bindings = cfg.get("bindings", {})
            if bindings.get("relative"):
                width = max(1.0, self.card_size.width())
                height = max(1.0, self.card_size.height())
                anchor = bindings.setdefault("anchor", {})
                anchor["x"] = item.pos().x() / width
                anchor["y"] = item.pos().y() / height
        return cfg

    # ------------------------------------------------------------------
    def update_item_zvalue(self, item_id: str, z_value: float):
        item = self.scene_items.get(item_id)
        if not item:
            return
        item.setZValue(z_value)
        if self.edit_mode == "template":
            cfg = self.layout.setdefault("items", {}).setdefault(item_id, {})
            cfg["z"] = z_value

    # ------------------------------------------------------------------
    def set_axis_lock(self, item_id: str, lock_x: Optional[bool] = None, lock_y: Optional[bool] = None):
        if self.edit_mode != "template":
            return
        cfg = self.layout.setdefault("items", {}).setdefault(item_id, {})
        bindings = cfg.setdefault("bindings", {})
        if lock_x is not None:
            bindings["lock_x"] = lock_x
        if lock_y is not None:
            bindings["lock_y"] = lock_y

    # ------------------------------------------------------------------
    def set_item_locked(self, item_id: str, locked: bool):
        item = self.scene_items.get(item_id)
        if not item:
            return
        item.setFlag(QGraphicsItem.ItemIsMovable, not (locked or self.template_locked))
        if self.edit_mode == "template":
            cfg = self.layout.setdefault("items", {}).setdefault(item_id, {})
            cfg["locked"] = locked

    # ------------------------------------------------------------------
    def apply_shadow(self, item_id: str, color: QColor, offset: Tuple[float, float], blur: float):
        item = self.scene_items.get(item_id)
        if not isinstance(item, QGraphicsTextItem):
            return
        effect = QGraphicsDropShadowEffect()
        effect.setColor(color)
        effect.setOffset(offset[0], offset[1])
        effect.setBlurRadius(blur)
        item.setGraphicsEffect(effect)
        if self.edit_mode == "template":
            cfg = self.layout.setdefault("items", {}).setdefault(item_id, {})
            cfg.setdefault("shadow", {})
            cfg["shadow"].update({"color": color.name(QColor.HexArgb), "offset": [offset[0], offset[1]], "blur": blur})

    # ------------------------------------------------------------------
    def get_layout_path(self) -> str:
        return self.layout_path
