from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QSpinBox, QComboBox, QColorDialog, QFileDialog, QCheckBox
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Signal


class PropertyPanel(QWidget):
    settingsChanged = Signal(object, dict)   # item, new_data

    def __init__(self, parent=None):
        super().__init__(parent)

        self.item = None
        self.build_ui()

    # ───────────────────────────────────────────────
    # UI побудова
    # ───────────────────────────────────────────────
    def build_ui(self):
        layout = QVBoxLayout(self)

        # Назва елементу
        self.lbl_title = QLabel("Element: ---")
        layout.addWidget(self.lbl_title)

        # X
        self.spin_x = QSpinBox()
        self.spin_x.setRange(-5000, 5000)
        layout.addWidget(self._row("X:", self.spin_x))

        # Y
        self.spin_y = QSpinBox()
        self.spin_y.setRange(-5000, 5000)
        layout.addWidget(self._row("Y:", self.spin_y))

        # Width
        self.spin_w = QSpinBox()
        self.spin_w.setRange(1, 5000)
        layout.addWidget(self._row("Width:", self.spin_w))

        # Height
        self.spin_h = QSpinBox()
        self.spin_h.setRange(1, 5000)
        layout.addWidget(self._row("Height:", self.spin_h))

        # Тип
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["text", "icon"])
        layout.addWidget(self._row("Type:", self.cmb_type))

        # ───── TEXT поля ─────
        self.edit_text = QLineEdit()
        layout.addWidget(self._row("Text:", self.edit_text))

        # Font
        self.edit_font = QLineEdit()
        layout.addWidget(self._row("Font:", self.edit_font))

        # Font size
        self.spin_fs = QSpinBox()
        self.spin_fs.setRange(1, 200)
        layout.addWidget(self._row("Font size:", self.spin_fs))

        # Bold
        self.chk_bold = QCheckBox("Bold")
        layout.addWidget(self.chk_bold)

        # Italic
        self.chk_italic = QCheckBox("Italic")
        layout.addWidget(self.chk_italic)

        # Alignment
        self.cmb_align = QComboBox()
        self.cmb_align.addItems(["left", "center", "right"])
        layout.addWidget(self._row("Align:", self.cmb_align))

        # Text color
        self.btn_text_color = QPushButton("Text Color")
        self.btn_text_color.clicked.connect(lambda: self.pick_color("text_color"))
        layout.addWidget(self.btn_text_color)

        # ───── ICON поля ─────
        self.edit_icon_path = QLineEdit()
        layout.addWidget(self._row("Icon:", self.edit_icon_path))

        self.btn_icon_browse = QPushButton("Browse")
        self.btn_icon_browse.clicked.connect(self.pick_icon)
        layout.addWidget(self.btn_icon_browse)

        # ───── ЕФЕКТИ ─────
        # Opacity
        self.spin_opacity = QSpinBox()
        self.spin_opacity.setRange(0, 100)
        layout.addWidget(self._row("Opacity %:", self.spin_opacity))

        # Outline width
        self.spin_outline_w = QSpinBox()
        self.spin_outline_w.setRange(0, 20)
        layout.addWidget(self._row("Outline w:", self.spin_outline_w))

        # Outline color
        self.btn_outline_color = QPushButton("Outline Color")
        self.btn_outline_color.clicked.connect(lambda: self.pick_color("outline_color"))
        layout.addWidget(self.btn_outline_color)

        # Shadow enabled
        self.chk_shadow = QCheckBox("Shadow")
        layout.addWidget(self.chk_shadow)

        # Shadow blur
        self.spin_shadow_blur = QSpinBox()
        self.spin_shadow_blur.setRange(0, 100)
        layout.addWidget(self._row("Shadow blur:", self.spin_shadow_blur))

        # Shadow offset X
        self.spin_shadow_x = QSpinBox()
        self.spin_shadow_x.setRange(-100, 100)
        layout.addWidget(self._row("Shadow X:", self.spin_shadow_x))

        # Shadow offset Y
        self.spin_shadow_y = QSpinBox()
        self.spin_shadow_y.setRange(-100, 100)
        layout.addWidget(self._row("Shadow Y:", self.spin_shadow_y))

        # Shadow opacity
        self.spin_shadow_opacity = QSpinBox()
        self.spin_shadow_opacity.setRange(0, 100)
        layout.addWidget(self._row("Shadow Opacity %:", self.spin_shadow_opacity))

        # Save button
        self.btn_apply = QPushButton("Apply changes")
        self.btn_apply.clicked.connect(self.apply_changes)
        layout.addWidget(self.btn_apply)

        layout.addStretch()

    # ───────────────────────────────────────────────
    def _row(self, label, widget):
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(QLabel(label))
        h.addWidget(widget)
        return row

    # ───────────────────────────────────────────────
    # Завантаження обраного елемента
    # ───────────────────────────────────────────────
    def set_item(self, item):
        if item is None:
            return

        self.item = item
        d = item.data

        self.lbl_title.setText(f"Element: {item.element_name}")

        # Розташування і розмір
        self.spin_x.setValue(item.x())
        self.spin_y.setValue(item.y())
        self.spin_w.setValue(item.width())
        self.spin_h.setValue(item.height())

        # Тип
        self.cmb_type.setCurrentText(d["type"])

        # Text
        self.edit_text.setText(d.get("text", ""))

        self.edit_font.setText(d["font"])
        self.spin_fs.setValue(d["font_size"])
        self.chk_bold.setChecked(d["font_bold"])
        self.chk_italic.setChecked(d["font_italic"])
        self.cmb_align.setCurrentText(d["alignment"])

        # Colors
        self.text_color = QColor(d["text_color"])
        self.outline_color = QColor(d["outline_color"])

        # Icon
        self.edit_icon_path.setText(d["icon_path"] or "")

        # Opacity
        self.spin_opacity.setValue(int(d["opacity"] * 100))

        # Outline
        self.spin_outline_w.setValue(d["outline_width"])

        # Shadow
        self.chk_shadow.setChecked(d["shadow_enabled"])
        self.spin_shadow_blur.setValue(d["shadow_blur"])
        self.spin_shadow_x.setValue(d["shadow_offset_x"])
        self.spin_shadow_y.setValue(d["shadow_offset_y"])
        self.spin_shadow_opacity.setValue(int(d["shadow_opacity"] * 100))

    # ───────────────────────────────────────────────
    # Вибір кольору
    # ───────────────────────────────────────────────
    def pick_color(self, field):
        col = QColorDialog.getColor()
        if not col.isValid():
            return

        if field == "text_color":
            self.text_color = col
        elif field == "outline_color":
            self.outline_color = col

    # ───────────────────────────────────────────────
    # Вибір іконки
    # ───────────────────────────────────────────────
    def pick_icon(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose icon", "", "Images (*.png)")
        if path:
            self.edit_icon_path.setText(path)

    # ───────────────────────────────────────────────
    # Застосування змін
    # ───────────────────────────────────────────────
    def apply_changes(self):
        if self.item is None:
            return

        d = self.item.data

        # Розташування і розмір
        self.item.setGeometry(
            self.spin_x.value(),
            self.spin_y.value(),
            self.spin_w.value(),
            self.spin_h.value(),
        )

        # Тип
        d["type"] = self.cmb_type.currentText()

        # TEXT
        d["text"] = self.edit_text.text()
        d["font"] = self.edit_font.text()
        d["font_size"] = self.spin_fs.value()
        d["font_bold"] = self.chk_bold.isChecked()
        d["font_italic"] = self.chk_italic.isChecked()
        d["alignment"] = self.cmb_align.currentText()
        d["text_color"] = self.text_color.name()

        # ICON
        d["icon_path"] = self.edit_icon_path.text()

        # Opacity
        d["opacity"] = self.spin_opacity.value() / 100.0

        # Outline
        d["outline_width"] = self.spin_outline_w.value()
        d["outline_color"] = self.outline_color.name()

        # Shadow
        d["shadow_enabled"] = self.chk_shadow.isChecked()
        d["shadow_blur"] = self.spin_shadow_blur.value()
        d["shadow_offset_x"] = self.spin_shadow_x.value()
        d["shadow_offset_y"] = self.spin_shadow_y.value()
        d["shadow_opacity"] = self.spin_shadow_opacity.value() / 100.0

        # Оновити елемент
        self.item.update()

        # Надіслати сигнал у DragCanvas
        self.settingsChanged.emit(self.item, d)
