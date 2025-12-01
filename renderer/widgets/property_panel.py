from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import (
    QColorDialog,
    QFileDialog,
    QFontComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPixmapItem, QGraphicsTextItem


class PropertyPanel(QWidget):
    """Side panel with controls for the currently selected scene item."""

    selected_item_changed = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._current_item: Optional[QGraphicsItem] = None
        self._updating = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.labelType = QLabel("Елемент: [не вибрано]")
        layout.addWidget(self.labelType)

        # font controls ---------------------------------------------------
        layout.addWidget(QLabel("Шрифт"))
        self.fontCombo = QFontComboBox()
        layout.addWidget(self.fontCombo)

        layout.addWidget(QLabel("Розмір"))
        self.fontSize = QSpinBox()
        self.fontSize.setRange(6, 120)
        layout.addWidget(self.fontSize)

        self.colorButton = QPushButton("Колір тексту")
        layout.addWidget(self.colorButton)

        # coordinates -----------------------------------------------------
        coords_layout = QGridLayout()
        coords_layout.addWidget(QLabel("X"), 0, 0)
        self.posX = QSpinBox()
        self.posX.setRange(-2000, 4000)
        coords_layout.addWidget(self.posX, 0, 1)
        coords_layout.addWidget(QLabel("Y"), 1, 0)
        self.posY = QSpinBox()
        self.posY.setRange(-2000, 4000)
        coords_layout.addWidget(self.posY, 1, 1)
        layout.addLayout(coords_layout)

        # opacity ---------------------------------------------------------
        self.opacityLabel = QLabel("Прозорість: 100%")
        layout.addWidget(self.opacityLabel)
        self.opacitySlider = QSlider(Qt.Horizontal)
        self.opacitySlider.setRange(0, 100)
        self.opacitySlider.setValue(100)
        layout.addWidget(self.opacitySlider)

        # z-order ---------------------------------------------------------
        layer_row = QHBoxLayout()
        self.btnLayerUp = QPushButton("На верх")
        self.btnLayerDown = QPushButton("На низ")
        layer_row.addWidget(self.btnLayerUp)
        layer_row.addWidget(self.btnLayerDown)
        layout.addLayout(layer_row)

        # icon + locking --------------------------------------------------
        self.btnReplaceIcon = QPushButton("Замінити іконку")
        layout.addWidget(self.btnReplaceIcon)

        self.lockButton = QPushButton("🔓 Рухомий")
        self.lockButton.setCheckable(True)
        layout.addWidget(self.lockButton)

        layout.addStretch()

        # register slots --------------------------------------------------
        self.fontCombo.currentFontChanged.connect(self._on_font_changed)
        self.fontSize.valueChanged.connect(self._on_font_size_changed)
        self.colorButton.clicked.connect(self._choose_color)
        self.posX.valueChanged.connect(self._on_position_changed)
        self.posY.valueChanged.connect(self._on_position_changed)
        self.opacitySlider.valueChanged.connect(self._on_opacity_changed)
        self.btnLayerUp.clicked.connect(lambda: self._adjust_layer(1))
        self.btnLayerDown.clicked.connect(lambda: self._adjust_layer(-1))
        self.btnReplaceIcon.clicked.connect(self._replace_pixmap)
        self.lockButton.toggled.connect(self._toggle_lock)

        self._set_all_controls_enabled(False)

    # ------------------------------------------------------------------
    def bind_item(self, item: Optional[QGraphicsItem]) -> None:
        """Attach scene item to the panel controls."""
        self._current_item = item
        self._updating = True

        if not item:
            self.labelType.setText("Елемент: [не вибрано]")
            self._set_all_controls_enabled(False)
            self.selected_item_changed.emit(None)
            self._updating = False
            return

        self.labelType.setText(f"Елемент: {type(item).__name__}")
        self._set_all_controls_enabled(True)
        self._update_type_specific_states(item)

        pos = item.pos()
        self.posX.setValue(int(pos.x()))
        self.posY.setValue(int(pos.y()))

        self.opacitySlider.setValue(int(item.opacity() * 100))
        self._update_opacity_label()

        if isinstance(item, QGraphicsTextItem):
            font = item.font()
            self.fontCombo.setCurrentFont(font)
            self.fontSize.setValue(max(font.pointSize(), 6))
            self._update_color_button(item.defaultTextColor())
        else:
            self.fontCombo.setCurrentFont(QFont())
            self.fontSize.setValue(12)
            self._update_color_button(QColor("#999"))

        locked = bool(item.data(Qt.UserRole))
        self.lockButton.blockSignals(True)
        self.lockButton.setChecked(locked)
        self._update_lock_button_text(locked)
        self.lockButton.blockSignals(False)

        self.selected_item_changed.emit(item)
        self._updating = False

    # ------------------------------------------------------------------
    def _set_all_controls_enabled(self, enabled: bool) -> None:
        widgets = [
            self.fontCombo,
            self.fontSize,
            self.colorButton,
            self.posX,
            self.posY,
            self.opacitySlider,
            self.btnLayerUp,
            self.btnLayerDown,
            self.btnReplaceIcon,
            self.lockButton,
        ]
        for widget in widgets:
            widget.setEnabled(enabled)
        if not enabled:
            self.opacityLabel.setText("Прозорість: 100%")

    # ------------------------------------------------------------------
    def _update_type_specific_states(self, item: QGraphicsItem) -> None:
        is_text = isinstance(item, QGraphicsTextItem)
        self.fontCombo.setEnabled(is_text)
        self.fontSize.setEnabled(is_text)
        self.colorButton.setEnabled(is_text)

        is_pixmap = isinstance(item, QGraphicsPixmapItem)
        self.btnReplaceIcon.setEnabled(is_pixmap)

    # ------------------------------------------------------------------
    def _on_font_changed(self, font: QFont) -> None:
        if self._updating:
            return
        text_item = self._get_text_item()
        if not text_item:
            return
        current_font = text_item.font()
        current_font.setFamily(font.family())
        text_item.setFont(current_font)

    # ------------------------------------------------------------------
    def _on_font_size_changed(self, size: int) -> None:
        if self._updating:
            return
        text_item = self._get_text_item()
        if not text_item:
            return
        font = text_item.font()
        font.setPointSize(size)
        text_item.setFont(font)

    # ------------------------------------------------------------------
    def _choose_color(self) -> None:
        text_item = self._get_text_item()
        if not text_item:
            return
        color = QColorDialog.getColor(text_item.defaultTextColor(), self)
        if color.isValid():
            text_item.setDefaultTextColor(color)
            self._update_color_button(color)

    # ------------------------------------------------------------------
    def _update_color_button(self, color: QColor) -> None:
        self.colorButton.setStyleSheet(
            f"background-color: {color.name()}; color: {'black' if color.lightness() > 128 else 'white'}"
        )

    # ------------------------------------------------------------------
    def _on_position_changed(self) -> None:
        if self._updating or not self._current_item:
            return
        self._current_item.setPos(self.posX.value(), self.posY.value())

    # ------------------------------------------------------------------
    def _on_opacity_changed(self, value: int) -> None:
        if self._updating or not self._current_item:
            return
        self._current_item.setOpacity(value / 100.0)
        self._update_opacity_label()

    # ------------------------------------------------------------------
    def _update_opacity_label(self) -> None:
        self.opacityLabel.setText(f"Прозорість: {self.opacitySlider.value()}%")

    # ------------------------------------------------------------------
    def _adjust_layer(self, delta: int) -> None:
        if not self._current_item:
            return
        self._current_item.setZValue(self._current_item.zValue() + delta)

    # ------------------------------------------------------------------
    def _replace_pixmap(self) -> None:
        pixmap_item = self._get_pixmap_item()
        if not pixmap_item:
            return
        start_dir = str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Обрати іконку",
            start_dir,
            "Зображення (*.png *.jpg *.jpeg *.webp)"
        )
        if not path:
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return
        pixmap_item.setPixmap(pixmap)

    # ------------------------------------------------------------------
    def _toggle_lock(self, checked: bool) -> None:
        if not self._current_item:
            return
        self._current_item.setFlag(QGraphicsItem.ItemIsMovable, not checked)
        self._current_item.setFlag(QGraphicsItem.ItemIsSelectable, not checked)
        self._current_item.setData(Qt.UserRole, int(checked))
        self._update_lock_button_text(checked)

    # ------------------------------------------------------------------
    def _update_lock_button_text(self, locked: bool) -> None:
        self.lockButton.setText("🔒 Заблоковано" if locked else "🔓 Рухомий")

    # ------------------------------------------------------------------
    def _get_text_item(self) -> Optional[QGraphicsTextItem]:
        if isinstance(self._current_item, QGraphicsTextItem):
            return self._current_item
        return None

    # ------------------------------------------------------------------
    def _get_pixmap_item(self) -> Optional[QGraphicsPixmapItem]:
        if isinstance(self._current_item, QGraphicsPixmapItem):
            return self._current_item
        return None
"""Property panel for editing card template elements."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFontComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.paths import application_base_dir
from .card_scene_view import CardSceneView


class PropertyPanel(QWidget):
    """Right side property inspector linked to CardSceneView."""

    def __init__(self, scene_view: CardSceneView, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.scene_view = scene_view
        self.current_item_id: Optional[str] = None
        self._updating = False

        self.setMinimumWidth(320)
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)

        self.layout_header = QLabel("Template Layout")
        self.layout_header.setStyleSheet("font-weight: 600; font-size: 16px;")
        self.layout.addWidget(self.layout_header)

        self.layout_path_label = QLineEdit(self.scene_view.get_layout_path())
        self.layout_path_label.setReadOnly(True)
        self.layout_path_label.setStyleSheet("font-size: 11px; color: #999;")
        self.layout.addWidget(self.layout_path_label)

        layout_btn_row = QHBoxLayout()
        self.btn_save_layout = QPushButton("💾 Зберегти")
        self.btn_save_layout.clicked.connect(self.scene_view.save_layout)
        layout_btn_row.addWidget(self.btn_save_layout)
        self.btn_save_as = QPushButton("Зберегти як…")
        self.btn_save_as.clicked.connect(self._save_layout_as)
        layout_btn_row.addWidget(self.btn_save_as)
        self.btn_load_layout = QPushButton("Завантажити")
        self.btn_load_layout.clicked.connect(self._load_layout_dialog)
        layout_btn_row.addWidget(self.btn_load_layout)
        self.layout.addLayout(layout_btn_row)

        self.btn_background = QPushButton("Колір фону сцени")
        self.btn_background.clicked.connect(self._change_background)
        self.layout.addWidget(self.btn_background)

        self.item_title = QLabel("Елемент: —")
        self.item_title.setStyleSheet("font-weight: 600; margin-top: 12px;")
        self.layout.addWidget(self.item_title)

        form = QFormLayout()
        self.layout.addLayout(form)

        self.pos_x = QDoubleSpinBox()
        self.pos_x.setRange(-5000, 5000)
        self.pos_y = QDoubleSpinBox()
        self.pos_y.setRange(-5000, 5000)
        self.pos_x.valueChanged.connect(self._update_position)
        self.pos_y.valueChanged.connect(self._update_position)
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(self.pos_x)
        pos_layout.addWidget(self.pos_y)
        form.addRow("X / Y", pos_layout)

        self.size_w = QDoubleSpinBox()
        self.size_h = QDoubleSpinBox()
        for spin in (self.size_w, self.size_h):
            spin.setRange(0, 5000)
            spin.valueChanged.connect(self._update_size)
        size_layout = QHBoxLayout()
        size_layout.addWidget(self.size_w)
        size_layout.addWidget(self.size_h)
        form.addRow("W / H", size_layout)

        self.text_width_spin = QDoubleSpinBox()
        self.text_width_spin.setRange(0, 2000)
        self.text_width_spin.valueChanged.connect(self._update_text_width)
        form.addRow("Text width", self.text_width_spin)

        self.font_family = QFontComboBox()
        self.font_family.currentFontChanged.connect(self._update_font)
        form.addRow("Шрифт", self.font_family)

        self.font_size = QSpinBox()
        self.font_size.setRange(6, 120)
        self.font_size.valueChanged.connect(self._update_font)
        form.addRow("Розмір", self.font_size)

        font_flags = QHBoxLayout()
        self.chk_bold = QCheckBox("B")
        self.chk_bold.setStyleSheet("font-weight: 800;")
        self.chk_bold.toggled.connect(self._update_font)
        self.chk_italic = QCheckBox("I")
        self.chk_italic.setStyleSheet("font-style: italic;")
        self.chk_italic.toggled.connect(self._update_font)
        self.chk_underline = QCheckBox("U")
        self.chk_underline.setStyleSheet("text-decoration: underline;")
        self.chk_underline.toggled.connect(self._update_font)
        font_flags.addWidget(self.chk_bold)
        font_flags.addWidget(self.chk_italic)
        font_flags.addWidget(self.chk_underline)
        form.addRow("Стиль", font_flags)

        self.btn_font_color = QPushButton("Колір тексту")
        self.btn_font_color.clicked.connect(self._change_text_color)
        form.addRow("Колір", self.btn_font_color)

        self.outline_width = QDoubleSpinBox()
        self.outline_width.setRange(0, 20)
        self.outline_width.setSingleStep(0.5)
        self.outline_width.valueChanged.connect(self._update_outline)
        self.btn_outline_color = QPushButton("Колір обводки")
        self.btn_outline_color.clicked.connect(self._change_outline_color)
        outline_layout = QHBoxLayout()
        outline_layout.addWidget(self.outline_width)
        outline_layout.addWidget(self.btn_outline_color)
        form.addRow("Обводка", outline_layout)

        opacity_row = QHBoxLayout()
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.valueChanged.connect(self._update_opacity)
        self.opacity_value = QLabel("100%")
        opacity_row.addWidget(self.opacity_slider)
        opacity_row.addWidget(self.opacity_value)
        form.addRow("Прозорість", opacity_row)

        lock_row = QHBoxLayout()
        self.chk_lock_item = QCheckBox("Lock move")
        self.chk_lock_item.toggled.connect(self._toggle_item_lock)
        self.chk_lock_x = QCheckBox("Lock X")
        self.chk_lock_x.toggled.connect(self._toggle_axis_lock)
        self.chk_lock_y = QCheckBox("Lock Y")
        self.chk_lock_y.toggled.connect(self._toggle_axis_lock)
        lock_row.addWidget(self.chk_lock_item)
        lock_row.addWidget(self.chk_lock_x)
        lock_row.addWidget(self.chk_lock_y)
        form.addRow("Блокування", lock_row)

        self.btn_change_icon = QPushButton("Змінити іконку / PNG")
        self.btn_change_icon.clicked.connect(self._change_pixmap)
        form.addRow("Зображення", self.btn_change_icon)

        z_row = QHBoxLayout()
        self.z_spin = QDoubleSpinBox()
        self.z_spin.setRange(-50, 50)
        self.z_spin.valueChanged.connect(self._update_z_value)
        z_row.addWidget(self.z_spin)
        form.addRow("Z-index", z_row)

        shadow_group = QGroupBox("Drop shadow")
        shadow_layout = QFormLayout(shadow_group)
        self.shadow_color_btn = QPushButton("Колір")
        self.shadow_color_btn.clicked.connect(self._change_shadow_color)
        self.shadow_offset_x = QDoubleSpinBox()
        self.shadow_offset_y = QDoubleSpinBox()
        self.shadow_offset_x.setRange(-100, 100)
        self.shadow_offset_y.setRange(-100, 100)
        self.shadow_offset_x.valueChanged.connect(self._update_shadow)
        self.shadow_offset_y.valueChanged.connect(self._update_shadow)
        self.shadow_blur = QDoubleSpinBox()
        self.shadow_blur.setRange(0, 100)
        self.shadow_blur.valueChanged.connect(self._update_shadow)
        shadow_layout.addRow("Колір", self.shadow_color_btn)
        offset_row = QHBoxLayout()
        offset_row.addWidget(self.shadow_offset_x)
        offset_row.addWidget(self.shadow_offset_y)
        shadow_layout.addRow("Зміщення", offset_row)
        shadow_layout.addRow("Blur", self.shadow_blur)
        self.layout.addWidget(shadow_group)

        self._setup_log_viewers()

        self.scene_view.selectionChanged.connect(self._on_item_selected)
        self.scene_view.itemUpdated.connect(self._on_item_updated)
        self.scene_view.layoutLoaded.connect(self._on_layout_loaded)

        self._current_outline_color = QColor("#FFFFFF")
        self._current_font_color = QColor("#FFFFFF")
        self._current_shadow_color = QColor("#000000")

    # ------------------------------------------------------------------
    def _setup_log_viewers(self) -> None:
        self.error_log_path = application_base_dir() / "error.txt"
        self.app_log_path = application_base_dir() / "application.log"

        log_group = QGroupBox("Вивід консолі")
        log_layout = QVBoxLayout(log_group)

        self.log_tabs = QTabWidget()
        self.log_tabs.currentChanged.connect(self._refresh_logs)

        # Error log tab
        error_tab = QWidget()
        error_layout = QVBoxLayout(error_tab)
        self.chk_error_realtime = QCheckBox("Вести лог в реальному часі")
        self.chk_error_realtime.toggled.connect(self._toggle_realtime_logging)
        self.error_log_view = QPlainTextEdit()
        self.error_log_view.setReadOnly(True)
        self.error_log_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.error_log_view.setStyleSheet("font-family: Consolas, 'Courier New', monospace;")
        error_layout.addWidget(self.chk_error_realtime)
        error_layout.addWidget(self.error_log_view)
        self.log_tabs.addTab(error_tab, "Error log")

        # Application log tab
        app_tab = QWidget()
        app_layout = QVBoxLayout(app_tab)
        self.chk_app_realtime = QCheckBox("Вести лог в реальному часі")
        self.chk_app_realtime.toggled.connect(self._toggle_realtime_logging)
        self.app_log_view = QPlainTextEdit()
        self.app_log_view.setReadOnly(True)
        self.app_log_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.app_log_view.setStyleSheet("font-family: Consolas, 'Courier New', monospace;")
        app_layout.addWidget(self.chk_app_realtime)
        app_layout.addWidget(self.app_log_view)
        self.log_tabs.addTab(app_tab, "Лог програми")

        log_layout.addWidget(self.log_tabs)
        self.layout.addWidget(log_group)

        self.log_timer = QTimer(self)
        self.log_timer.setInterval(1000)
        self.log_timer.timeout.connect(self._refresh_logs)

        self._load_logs_once()

    # ------------------------------------------------------------------
    def _load_logs_once(self) -> None:
        self._update_log_view(self.error_log_path, self.error_log_view)
        self._update_log_view(self.app_log_path, self.app_log_view)

    # ------------------------------------------------------------------
    def _toggle_realtime_logging(self):
        if self.chk_error_realtime.isChecked():
            self._update_log_view(self.error_log_path, self.error_log_view)
        if self.chk_app_realtime.isChecked():
            self._update_log_view(self.app_log_path, self.app_log_view)

        if self.chk_error_realtime.isChecked() or self.chk_app_realtime.isChecked():
            if not self.log_timer.isActive():
                self.log_timer.start()
        else:
            self.log_timer.stop()

    # ------------------------------------------------------------------
    def _refresh_logs(self):
        if self.chk_error_realtime.isChecked():
            self._update_log_view(self.error_log_path, self.error_log_view)
        if self.chk_app_realtime.isChecked():
            self._update_log_view(self.app_log_path, self.app_log_view)

    # ------------------------------------------------------------------
    def _update_log_view(self, path, widget: QPlainTextEdit) -> None:
        widget.setPlainText(self._read_log_file(path))
        widget.verticalScrollBar().setValue(widget.verticalScrollBar().maximum())

    # ------------------------------------------------------------------
    def _read_log_file(self, path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return "Файл журналу не знайдено."
        except Exception as exc:  # pragma: no cover - UI helper
            return f"Не вдалося прочитати лог: {exc}"

    # ------------------------------------------------------------------
    def _on_layout_loaded(self, layout_dict: dict):
        self.layout_path_label.setText(self.scene_view.get_layout_path())

    # ------------------------------------------------------------------
    def _on_item_selected(self, item_id: str):
        self.current_item_id = item_id
        self._populate_from_config(self.scene_view.get_item_config(item_id))

    # ------------------------------------------------------------------
    def _on_item_updated(self, item_id: str, cfg: dict):
        if self.current_item_id != item_id:
            return
        self._populate_from_config(cfg)

    # ------------------------------------------------------------------
    def _populate_from_config(self, cfg: dict):
        self._updating = True
        try:
            self.item_title.setText(f"Елемент: {self.current_item_id}")
            pos = cfg.get("pos", {})
            self.pos_x.setValue(pos.get("x", 0))
            self.pos_y.setValue(pos.get("y", 0))
            size = cfg.get("size", {})
            self.size_w.setValue(size.get("w", 0))
            self.size_h.setValue(size.get("h", 0))
            self.text_width_spin.setValue(cfg.get("text_width", 0))
            font_cfg = cfg.get("font", {})
            self.font_family.setCurrentFont(QFont(font_cfg.get("family", "Arial")))
            if font_cfg.get("size"):
                self.font_size.setValue(int(font_cfg.get("size", 12)))
            self.chk_bold.setChecked(font_cfg.get("bold", False))
            self.chk_italic.setChecked(font_cfg.get("italic", False))
            self.chk_underline.setChecked(font_cfg.get("underline", False))
            self._current_font_color = QColor(cfg.get("color", "#FFFFFF"))
            self.btn_font_color.setStyleSheet(f"background:{self._current_font_color.name()};")
            self.outline_width.setValue(cfg.get("shadow", {}).get("blur", 0) / 2)
            self._current_outline_color = QColor(cfg.get("shadow", {}).get("color", "#000000"))
            self.btn_outline_color.setStyleSheet(f"background:{self._current_outline_color.name()};")
            opacity = int(cfg.get("opacity", 1.0) * 100)
            self.opacity_slider.setValue(opacity)
            self.opacity_value.setText(f"{opacity}%")
            bindings = cfg.get("bindings", {})
            self.chk_lock_x.setChecked(bindings.get("lock_x", False))
            self.chk_lock_y.setChecked(bindings.get("lock_y", False))
            self.chk_lock_item.setChecked(cfg.get("locked", False))
            self.z_spin.setValue(cfg.get("z", 0))
            shadow = cfg.get("shadow", {})
            self._current_shadow_color = QColor(shadow.get("color", "#000000"))
            self.shadow_color_btn.setStyleSheet(f"background:{self._current_shadow_color.name()};")
            offset = shadow.get("offset", [0, 0])
            self.shadow_offset_x.setValue(offset[0])
            self.shadow_offset_y.setValue(offset[1])
            self.shadow_blur.setValue(shadow.get("blur", 0))
            item_type = cfg.get("type", "text")
            self._toggle_controls_for_type(item_type)
        finally:
            self._updating = False

    # ------------------------------------------------------------------
    def _toggle_controls_for_type(self, item_type: str):
        is_text = item_type == "text"
        self.text_width_spin.setEnabled(is_text)
        self.font_family.setEnabled(is_text)
        self.font_size.setEnabled(is_text)
        self.chk_bold.setEnabled(is_text)
        self.chk_italic.setEnabled(is_text)
        self.chk_underline.setEnabled(is_text)
        self.btn_font_color.setEnabled(is_text)
        self.outline_width.setEnabled(is_text)
        self.btn_outline_color.setEnabled(is_text)
        self.shadow_color_btn.setEnabled(is_text)
        self.shadow_offset_x.setEnabled(is_text)
        self.shadow_offset_y.setEnabled(is_text)
        self.shadow_blur.setEnabled(is_text)
        self.btn_change_icon.setEnabled(item_type in {"image", "pixmap", "icon"})
        self.size_w.setEnabled(item_type != "text")
        self.size_h.setEnabled(item_type != "text")

    # ------------------------------------------------------------------
    def _update_position(self):
        if self._updating or not self.current_item_id:
            return
        self.scene_view.update_item_position(
            self.current_item_id, (self.pos_x.value(), self.pos_y.value())
        )

    # ------------------------------------------------------------------
    def _update_size(self):
        if self._updating or not self.current_item_id:
            return
        self.scene_view.update_item_size(
            self.current_item_id, (self.size_w.value(), self.size_h.value())
        )

    # ------------------------------------------------------------------
    def _update_text_width(self, value: float):
        if self._updating or not self.current_item_id:
            return
        self.scene_view.update_text_width(self.current_item_id, value)

    # ------------------------------------------------------------------
    def _update_font(self, *_):
        if self._updating or not self.current_item_id:
            return
        font = QFont(self.font_family.currentFont())
        font.setPointSize(self.font_size.value())
        font.setBold(self.chk_bold.isChecked())
        font.setItalic(self.chk_italic.isChecked())
        font.setUnderline(self.chk_underline.isChecked())
        self.scene_view.update_font(self.current_item_id, font)

    # ------------------------------------------------------------------
    def _change_text_color(self):
        color = QColorDialog.getColor(self._current_font_color, self)
        if not color.isValid() or not self.current_item_id:
            return
        self._current_font_color = color
        self.btn_font_color.setStyleSheet(f"background:{color.name()};")
        self.scene_view.update_text_color(self.current_item_id, color)

    # ------------------------------------------------------------------
    def _change_outline_color(self):
        color = QColorDialog.getColor(self._current_outline_color, self)
        if not color.isValid():
            return
        self._current_outline_color = color
        self.btn_outline_color.setStyleSheet(f"background:{color.name()};")
        self._update_outline()

    # ------------------------------------------------------------------
    def _update_outline(self):
        if self._updating or not self.current_item_id:
            return
        self.scene_view.apply_outline(
            self.current_item_id, self._current_outline_color, self.outline_width.value()
        )

    # ------------------------------------------------------------------
    def _update_opacity(self, value: int):
        if self._updating or not self.current_item_id:
            return
        self.opacity_value.setText(f"{value}%")
        self.scene_view.update_item_opacity(self.current_item_id, value / 100)

    # ------------------------------------------------------------------
    def _toggle_item_lock(self, checked: bool):
        if self._updating or not self.current_item_id:
            return
        self.scene_view.set_item_locked(self.current_item_id, checked)

    # ------------------------------------------------------------------
    def _toggle_axis_lock(self, _):
        if self._updating or not self.current_item_id:
            return
        self.scene_view.set_axis_lock(
            self.current_item_id,
            lock_x=self.chk_lock_x.isChecked(),
            lock_y=self.chk_lock_y.isChecked(),
        )

    # ------------------------------------------------------------------
    def _change_pixmap(self):
        if not self.current_item_id:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Обрати PNG", "", "Images (*.png *.jpg *.webp)")
        if not path:
            return
        self.scene_view.change_icon_source(self.current_item_id, path)

    # ------------------------------------------------------------------
    def _update_z_value(self):
        if self._updating or not self.current_item_id:
            return
        self.scene_view.update_item_zvalue(self.current_item_id, self.z_spin.value())

    # ------------------------------------------------------------------
    def _change_shadow_color(self):
        color = QColorDialog.getColor(self._current_shadow_color, self)
        if not color.isValid():
            return
        self._current_shadow_color = color
        self.shadow_color_btn.setStyleSheet(f"background:{color.name()};")
        self._update_shadow()

    # ------------------------------------------------------------------
    def _update_shadow(self):
        if self._updating or not self.current_item_id:
            return
        self.scene_view.apply_shadow(
            self.current_item_id,
            self._current_shadow_color,
            (self.shadow_offset_x.value(), self.shadow_offset_y.value()),
            self.shadow_blur.value(),
        )

    # ------------------------------------------------------------------
    def _change_background(self):
        color = QColorDialog.getColor(parent=self)
        if not color.isValid():
            return
        self.scene_view.set_background_color(color)

    # ------------------------------------------------------------------
    def _save_layout_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Зберегти layout", "template_layout.json", "JSON (*.json)")
        if not path:
            return
        self.scene_view.save_layout(path)
        self.layout_path_label.setText(path)

    # ------------------------------------------------------------------
    def _load_layout_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Обрати layout", "", "JSON (*.json)")
        if not path:
            return
        self.scene_view.load_template(path)
        self.layout_path_label.setText(path)
