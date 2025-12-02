from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import (
    QPainter, QColor, QPen, QFont, QPixmap, QBrush
)
from PySide6.QtCore import Qt, QRect, QPoint, Signal
import json
import os


# ============================================================
# DraggableElement V2.5 — з підтримкою zoom + snap-to-grid
# ============================================================
class DraggableElement(QWidget):
    HANDLE_SIZE = 10

    DEFAULT_DATA = {
        "type": "text",
        "text": "",
        "font": "Arial",
        "font_size": 22,
        "font_bold": False,
        "font_italic": False,
        "alignment": "left",
        "text_color": "#ffffff",

        "opacity": 1.0,

        "outline_width": 0,
        "outline_color": "#000000",

        "shadow_enabled": False,
        "shadow_blur": 5,
        "shadow_offset_x": 2,
        "shadow_offset_y": 2,
        "shadow_opacity": 0.5,

        "icon_path": None,
        "icon_tint": "#ffffff",
    }

    def __init__(self, name, parent, x, y, w, h, data=None):
        super().__init__(parent)

        merged = DraggableElement.DEFAULT_DATA.copy()
        if data:
            merged.update(data)
        self.data = merged

        self.element_name = name
        self.setGeometry(x, y, w, h)

        self.dragging = False
        self.resizing = False
        self.selected = False
        self.resize_direction = None
        self.drag_offset = QPoint(0, 0)

        self.setMouseTracking(True)

    # --------------------------------------------------------
    # Alignment
    # --------------------------------------------------------
    def get_alignment_flag(self):
        al = self.data["alignment"]
        if al == "left":
            return Qt.AlignLeft | Qt.AlignVCenter
        if al == "right":
            return Qt.AlignRight | Qt.AlignVCenter
        if al == "center":
            return Qt.AlignHCenter | Qt.AlignVCenter
        return Qt.AlignLeft

    # --------------------------------------------------------
    # Paint
    # --------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        data = self.data
        w, h = self.width(), self.height()

        if self.selected:
            painter.fillRect(self.rect(), QColor(60, 60, 60, 90))

        painter.setOpacity(data.get("opacity", 1.0))

        # ICON
        if data["type"] == "icon" and data["icon_path"]:
            pix = QPixmap(data["icon_path"])
            if not pix.isNull():
                scaled = pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                painter.drawPixmap(
                    (w - scaled.width()) // 2,
                    (h - scaled.height()) // 2,
                    scaled
                )

        # TEXT
        if data["type"] == "text":
            font = QFont(data["font"], data["font_size"])
            font.setBold(data["font_bold"])
            font.setItalic(data["font_italic"])
            painter.setFont(font)

            text = data.get("text", self.element_name)

            # outline
            if data["outline_width"] > 0:
                pen = QPen(QColor(data["outline_color"]))
                pen.setWidth(data["outline_width"])
                painter.setPen(pen)
                painter.drawText(self.rect(), self.get_alignment_flag(), text)

            painter.setPen(QColor(data["text_color"]))
            painter.drawText(self.rect(), self.get_alignment_flag(), text)

        # resize handles
        if self.selected:
            self.draw_resize_handles(painter)

        painter.end()

    def draw_resize_handles(self, painter):
        s = self.HANDLE_SIZE
        rect = self.rect()
        handles = [
            QRect(0, 0, s, s),
            QRect(rect.width() - s, 0, s, s),
            QRect(0, rect.height() - s, s, s),
            QRect(rect.width() - s, rect.height() - s, s, s),
        ]

        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        for h in handles:
            painter.drawRect(h)

    # --------------------------------------------------------
    # Mouse Events
    # --------------------------------------------------------
    def mousePressEvent(self, event):
        self.selected = True
        self.update()

        if self.is_on_resize_handle(event.pos()):
            self.resizing = True
            self.resize_direction = self.detect_resize_handle(event.pos())
        else:
            self.dragging = True
            self.drag_offset = event.pos()

        self.parent().itemSelected.emit(self)

    def mouseMoveEvent(self, event):
        parent = self.parent()
        zoom = parent.zoom

        # DRAG
        if self.dragging:
            delta = (event.pos() - self.drag_offset) / zoom
            new_pos = self.pos() + delta

            # snap-to-grid
            new_pos.setX(round(new_pos.x() / 16) * 16)
            new_pos.setY(round(new_pos.y() / 16) * 16)

            self.move(new_pos)

        # RESIZE
        if self.resizing:
            self.perform_resize(event.pos(), zoom)

        self.update()

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.resizing = False

    # --------------------------------------------------------
    # resize logic
    # --------------------------------------------------------
    def is_on_resize_handle(self, pos):
        s = self.HANDLE_SIZE
        rect = self.rect()
        handles = [
            QRect(0, 0, s, s),
            QRect(rect.width() - s, 0, s, s),
            QRect(0, rect.height() - s, s, s),
            QRect(rect.width() - s, rect.height() - s, s, s),
        ]
        return any(h.contains(pos) for h in handles)

    def detect_resize_handle(self, pos):
        s = self.HANDLE_SIZE
        rect = self.rect()
        if QRect(0, 0, s, s).contains(pos): return "topleft"
        if QRect(rect.width() - s, 0, s, s).contains(pos): return "topright"
        if QRect(0, rect.height() - s, s, s).contains(pos): return "bottomleft"
        if QRect(rect.width() - s, rect.height() - s, s, s).contains(pos): return "bottomright"
        return None

    def perform_resize(self, pos, zoom):
        pos = pos / zoom
        x, y, w, h = self.x(), self.y(), self.width(), self.height()

        if self.resize_direction == "bottomright":
            new_w = pos.x()
            new_h = pos.y()

        elif self.resize_direction == "bottomleft":
            new_w = w - pos.x()
            x = x + pos.x()
            new_h = h
        elif self.resize_direction == "topright":
            new_h = h - pos.y()
            y = y + pos.y()
            new_w = w
        else:
            new_w = w - pos.x()
            new_h = h - pos.y()
            x = x + pos.x()
            y = y + pos.y()

        # snap-to-grid
        new_w = round(new_w / 16) * 16
        new_h = round(new_h / 16) * 16
        x = round(x / 16) * 16
        y = round(y / 16) * 16

        if new_w < 16: new_w = 16
        if new_h < 16: new_h = 16

        self.setGeometry(x, y, new_w, new_h)


# ============================================================
# DragCanvas V3 — Adaptive + Zoom + Pan + Grid + Guides
# ============================================================
class DragCanvas(QWidget):
    itemSelected = Signal(object)

    CARD_W = 768
    CARD_H = 1088

    def __init__(self, template_path, parent=None):
        super().__init__(parent)
        self.setMinimumSize(768, 1088)

        self.zoom = 1.0
        self.pan_offset = QPoint(0, 0)
        self.panning = False
        self.last_pan_pos = None

        self.art_pixmap = None
        self.template_path = template_path
        self.template = self.load_template()
        self.elements = {}
        self.init_elements()

        self.setMouseTracking(True)

    # --------------------------------------------------------
    def load_template(self):
        if not os.path.exists(self.template_path):
            return {}
        with open(self.template_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def init_elements(self):
        for name, block in self.template.items():
            x = block.get("x", 0)
            y = block.get("y", 0)
            w = block.get("w", 120)
            h = block.get("h", 40)

            elem = DraggableElement(name, self, x, y, w, h, block)
            self.elements[name] = elem
    
    
    
    def save_template(self):
        data = {}

        for name, elem in self.elements.items():
            d = elem.data

            data[name] = {
                "type": d["type"],
                "text": d.get("text"),
                "x": elem.x(),
                "y": elem.y(),
                "w": elem.width(),
                "h": elem.height(),

                "font": d["font"],
                "font_size": d["font_size"],
                "font_bold": d["font_bold"],
                "font_italic": d["font_italic"],

                "alignment": d["alignment"],
                "text_color": d["text_color"],

                "opacity": d["opacity"],
                "outline_width": d["outline_width"],
                "outline_color": d["outline_color"],

                "shadow_enabled": d["shadow_enabled"],
                "shadow_blur": d["shadow_blur"],
                "shadow_offset_x": d["shadow_offset_x"],
                "shadow_offset_y": d["shadow_offset_y"],
                "shadow_opacity": d["shadow_opacity"],

                "icon_path": d["icon_path"],
                "icon_tint": d["icon_tint"],
            }

        with open(self.template_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    
    
    # --------------------------------------------------------
    # ART (768×1088)
    # --------------------------------------------------------
    def set_art_pixmap(self, pixmap):
        img = QPixmap(pixmap)
        self.art_pixmap = img.scaled(
            self.CARD_W, self.CARD_H,
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation
        )
        self.update()

    # --------------------------------------------------------
    # PAINT CANVAS
    # --------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # ============================
        # 1) Adaptive Fit to window
        # ============================
        available_w = self.width()
        available_h = self.height()

        fit_scale = min(
            available_w / self.CARD_W,
            available_h / self.CARD_H
        )

        total_scale = fit_scale * self.zoom

        center_x = (available_w - self.CARD_W * total_scale) / 2
        center_y = (available_h - self.CARD_H * total_scale) / 2

        painter.translate(center_x + self.pan_offset.x(),
                          center_y + self.pan_offset.y())

        painter.scale(total_scale, total_scale)

        # ============================
        # 2) Draw ART
        # ============================
        if self.art_pixmap:
            painter.drawPixmap(0, 0, self.art_pixmap)

        # ============================
        # 3) Grid 16px
        # ============================
        grid_pen = QPen(QColor(70, 70, 70), 1)

        painter.setPen(grid_pen)
        for x in range(0, self.CARD_W, 16):
            painter.drawLine(x, 0, x, self.CARD_H)
        for y in range(0, self.CARD_H, 16):
            painter.drawLine(0, y, self.CARD_W, y)

        # ============================
        # 4) Guides: center lines
        # ============================
        guide_pen = QPen(QColor(255, 0, 0, 120), 2)
        painter.setPen(guide_pen)

        painter.drawLine(self.CARD_W / 2, 0, self.CARD_W / 2, self.CARD_H)
        painter.drawLine(0, self.CARD_H / 2, self.CARD_W, self.CARD_H / 2)

        painter.end()

    # --------------------------------------------------------
    # ZOOM
    # --------------------------------------------------------
    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.zoom *= 1.1
        else:
            self.zoom /= 1.1

        self.zoom = max(0.2, min(4.0, self.zoom))
        self.update()

    # --------------------------------------------------------
    # PAN (Shift + ЛКМ)
    # --------------------------------------------------------
    def mousePressEvent(self, event):
        modifiers = QApplication.keyboardModifiers()

        if event.button() == Qt.LeftButton and modifiers == Qt.ShiftModifier:
            self.panning = True
            self.last_pan_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self.panning:
            diff = event.pos() - self.last_pan_pos
            self.pan_offset += diff
            self.last_pan_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        self.panning = False
        self.last_pan_pos = None
