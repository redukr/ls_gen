from PySide6.QtWidgets import QWidget
from PySide6.QtGui import (
    QPainter, QColor, QPen, QFont, QFontMetrics, QPixmap, QBrush
)
from PySide6.QtCore import Qt, QRect, QPoint, Signal
import json
import os


# ───────────────────────────────────────────────
# DraggableElement V2.0 — кастомний елемент
# ───────────────────────────────────────────────
class DraggableElement(QWidget):
    HANDLE_SIZE = 10  # resize точки

    def __init__(self, name, parent, x, y, w, h, data=None):
        super().__init__(parent)

        self.element_name = name
        self.setGeometry(x, y, w, h)

        # Якщо немає JSON — створюємо чисту структуру
        self.data = data if data else {
            "type": "text",
            "text": name,

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

        self.dragging = False
        self.resizing = False
        self.selected = False
        self.resize_direction = None
        self.drag_offset = QPoint(0, 0)

        self.setMouseTracking(True)

    # ───────────────────────────────────────────────
    # Alignment
    # ───────────────────────────────────────────────
    def get_alignment_flag(self):
        al = self.data["alignment"]
        if al == "left":
            return Qt.AlignLeft | Qt.AlignVCenter
        if al == "right":
            return Qt.AlignRight | Qt.AlignVCenter
        if al == "center":
            return Qt.AlignHCenter | Qt.AlignVCenter
        return Qt.AlignLeft

    # ───────────────────────────────────────────────
    # Рендерінг
    # ───────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        data = self.data
        w, h = self.width(), self.height()

        # Підсвітка при виборі
        if self.selected:
            painter.fillRect(self.rect(), QColor(60, 60, 60, 90))

        painter.setOpacity(data["opacity"])

        # Якщо іконка
        if data["type"] == "icon" and data["icon_path"]:
            pix = QPixmap(data["icon_path"])
            if not pix.isNull():
                scaled = pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                painter.drawPixmap(
                    (w - scaled.width()) // 2,
                    (h - scaled.height()) // 2,
                    scaled
                )

        # Якщо текст
        if data["type"] == "text":
            font = QFont(data["font"], data["font_size"])
            font.setBold(data["font_bold"])
            font.setItalic(data["font_italic"])
            painter.setFont(font)

            text = data.get("text", self.element_name)

            # outline
            if data["outline_width"] > 0:
                outline_pen = QPen(QColor(data["outline_color"]))
                outline_pen.setWidth(data["outline_width"])
                painter.setPen(outline_pen)
                painter.drawText(self.rect(), self.get_alignment_flag(), text)

            # основний текст
            painter.setPen(QColor(data["text_color"]))
            painter.drawText(self.rect(), self.get_alignment_flag(), text)

        # Resize-handles
        if self.selected:
            self.draw_resize_handles(painter)
    
        painter.end()
    
    # ───────────────────────────────────────────────
    def draw_resize_handles(self, painter):
        s = self.HANDLE_SIZE
        rect = self.rect()
        handles = [
            QRect(0, 0, s, s),  # top-left
            QRect(rect.width() - s, 0, s, s),  # top-right
            QRect(0, rect.height() - s, s, s),  # bottom-left
            QRect(rect.width() - s, rect.height() - s, s, s),  # bottom-right
        ]

        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        for h in handles:
            painter.drawRect(h)

    # ───────────────────────────────────────────────
    # Події миші
    # ───────────────────────────────────────────────
    def mousePressEvent(self, event):
        self.selected = True
        self.update()

        # Перевіряємо чи resize
        if self.is_on_resize_handle(event.pos()):
            self.resizing = True
            self.resize_direction = self.detect_resize_handle(event.pos())
        else:
            # Drag
            self.dragging = True
            self.drag_offset = event.pos()

        self.parent().itemSelected.emit(self)

    def mouseMoveEvent(self, event):
        if self.dragging:
            new_pos = self.mapToParent(event.pos() - self.drag_offset)
            self.move(new_pos)

        if self.resizing:
            self.perform_resize(event.pos())

        self.update()

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.resizing = False

    # ───────────────────────────────────────────────
    # Resize логіка
    # ───────────────────────────────────────────────
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
        if QRect(rect.width()-s, 0, s, s).contains(pos): return "topright"
        if QRect(0, rect.height()-s, s, s).contains(pos): return "bottomleft"
        if QRect(rect.width()-s, rect.height()-s, s, s).contains(pos): return "bottomright"
        return None

    def perform_resize(self, pos):
        x, y, w, h = self.x(), self.y(), self.width(), self.height()

        if self.resize_direction == "bottomright":
            self.resize(pos.x(), pos.y())

        elif self.resize_direction == "bottomleft":
            new_w = w - pos.x()
            self.setGeometry(x + pos.x(), y, new_w, h)

        elif self.resize_direction == "topright":
            new_h = h - pos.y()
            self.setGeometry(x, y + pos.y(), w, new_h)

        elif self.resize_direction == "topleft":
            new_w = w - pos.x()
            new_h = h - pos.y()
            self.setGeometry(x + pos.x(), y + pos.y(), new_w, new_h)


# ───────────────────────────────────────────────
# DragCanvas V2.0 — робота з JSON + елементами
# ───────────────────────────────────────────────
class DragCanvas(QWidget):
    itemSelected = Signal(object)

    def __init__(self, template_path, parent=None):
        super().__init__(parent)
        
        self.art_pixmap = None
        self.setFixedSize(768, 1088)

        self.template_path = template_path
        self.template = self.load_template()

        self.elements = {}
        self.selected_element = None

        self.init_elements()

        self.setStyleSheet("background-color: #222;")

    # ───────────────────────────────────────────────
    def load_template(self):
        if not os.path.exists(self.template_path):
            return {}

        with open(self.template_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ───────────────────────────────────────────────
    def init_elements(self):
        for name, block in self.template.items():
            x = block.get("x", 0)
            y = block.get("y", 0)
            w = block.get("w", 120)
            h = block.get("h", 40)

            elem = DraggableElement(name, self, x, y, w, h, block)
            self.elements[name] = elem

    # ───────────────────────────────────────────────
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
    
    def set_art_pixmap(self, pixmap):
        # Масштабуємо арт рівно під картку
        scaled = pixmap.scaled(
            768, 1088,
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation
        )
        self.art_pixmap = scaled
        self.update()
        
    # ───────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.art_pixmap:
            painter.drawPixmap(0, 0, self.art_pixmap)
        else:
            painter.setBrush(QBrush(QColor(30, 30, 30)))
            painter.drawRect(self.rect())

        painter.end()

