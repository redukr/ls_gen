from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtCore import Qt, QRect, QPoint

import json
import os


class DraggableElement(QLabel):
    def __init__(self, name, parent, x, y, w, h):
        super().__init__(parent)
        self.element_name = name
        self.setGeometry(x, y, w, h)
        self.setStyleSheet("background-color: rgba(40,40,40,120); color: white; border: 1px solid #888;")
        self.setAlignment(Qt.AlignCenter)
        self.setText(name)
        self.offset = QPoint(0, 0)
        self.selected = False

    def mousePressEvent(self, event):
        self.offset = event.pos()
        self.selected = True
        self.update()

    def mouseMoveEvent(self, event):
        new_pos = self.mapToParent(event.pos() - self.offset)
        self.move(new_pos)
        self.update()

    def mouseReleaseEvent(self, event):
        self.selected = False
        self.update()


class DragCanvas(QWidget):
    def __init__(self, template_path, parent=None):
        super().__init__(parent)

        self.template_path = template_path
        self.template = self.load_template()

        self.elements = {}
        self.selected_element = None

        self.init_elements()

        self.setMinimumSize(600, 800)
        self.setStyleSheet("background-color: #222;")

    # ───────────────────────────────────────────────
    # Завантаження шаблону
    # ───────────────────────────────────────────────
    def load_template(self):
        if not os.path.exists(self.template_path):
            return {}

        with open(self.template_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ───────────────────────────────────────────────
    # Створення draggable-елементів
    # ───────────────────────────────────────────────
    def init_elements(self):
        for key, block in self.template.items():
            x = block.get("x", 0)
            y = block.get("y", 0)
            w = block.get("w", 20)
            h = block.get("h", 10)

            elem = DraggableElement(key, self, x, y, w, h)
            self.elements[key] = elem

    # ───────────────────────────────────────────────
    # Збереження в template.json
    # ───────────────────────────────────────────────
    def save_template(self):
        data = {}

        for name, elem in self.elements.items():
            x = elem.x()
            y = elem.y()
            w = elem.width()
            h = elem.height()

            data[name] = {
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "font": "Montserrat.ttf",
                "size": 22
            }

        with open(self.template_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    # ───────────────────────────────────────────────
    # Рендеринг (тільки фон і рамка)
    # ───────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect()

        painter.setBrush(QBrush(QColor(30,30,30)))
        painter.drawRect(rect)

        pen = QPen(QColor(90,90,90), 2)
        painter.setPen(pen)
        painter.drawRect(rect)

        painter.end()
