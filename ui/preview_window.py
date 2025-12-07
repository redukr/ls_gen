from __future__ import annotations

import os
from typing import List

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ai.app_ai import generate_previews
from ui.locales import ensure_language, get_section


class HoverPreviewLabel(QLabel):
    """Show a magnified view of the pixmap on hover."""

    def __init__(self, base_size: int = 192, zoom_factor: int = 3, parent=None):
        super().__init__(parent)
        self.base_size = base_size
        self.zoom_factor = zoom_factor
        self.original_pixmap = None
        self.zoom_label: QLabel | None = None
        self.setAlignment(Qt.AlignCenter)

    def set_preview(self, path: str | None):
        if path and os.path.isfile(path):
            pixmap = QPixmap(path)
            self.original_pixmap = pixmap
            self.setPixmap(
                pixmap.scaled(
                    self.base_size, self.base_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
        else:
            self.original_pixmap = None
            self.setPixmap(QPixmap())

    def enterEvent(self, event):  # noqa: N802
        super().enterEvent(event)
        if not self.original_pixmap:
            return
        if self.zoom_label is None:
            self.zoom_label = QLabel()
            self.zoom_label.setWindowFlags(Qt.ToolTip)
        scaled = self.original_pixmap.scaled(
            self.base_size * self.zoom_factor,
            self.base_size * self.zoom_factor,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.zoom_label.setPixmap(scaled)
        self.zoom_label.adjustSize()
        global_pos = self.mapToGlobal(self.rect().bottomRight())
        self.zoom_label.move(global_pos)
        self.zoom_label.show()

    def leaveEvent(self, event):  # noqa: N802
        super().leaveEvent(event)
        if self.zoom_label:
            self.zoom_label.hide()


class PreviewItem(QWidget):
    def __init__(self, like_label: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.image = HoverPreviewLabel()
        self.checkbox = QCheckBox(like_label)
        layout.addWidget(self.image)
        layout.addWidget(self.checkbox)
        self.setLayout(layout)

    def set_preview(self, preview: dict | None):
        if preview:
            self.image.set_preview(preview.get("path"))
        else:
            self.image.set_preview(None)
        self.checkbox.setChecked(False)


class PreviewGeneratorWorker(QWidget):
    finished = Signal(list)
    failed = Signal(str)

    def __init__(
        self,
        prompt: str,
        csv_path: str | None,
        model: str,
        width: int,
        height: int,
        style_hint: str,
        count: int,
        language: str,
        row_indices: list[int] | None = None,
    ):
        super().__init__()
        self.prompt = prompt
        self.csv_path = csv_path
        self.model = model
        self.width = width
        self.height = height
        self.style_hint = style_hint
        self.count = count
        self.language = language
        self.row_indices = row_indices

    def run(self):
        try:
            previews = generate_previews(
                self.prompt,
                self.csv_path,
                self.model,
                count=self.count,
                width=self.width,
                height=self.height,
                style_hint=self.style_hint,
                language=self.language,
                row_indices=self.row_indices,
            )
            self.finished.emit(previews)
        except Exception as exc:  # pragma: no cover - UI thread safety
            self.failed.emit(str(exc))


class PreviewGenWindow(QWidget):
    previewsSelected = Signal(list)

    def __init__(
        self,
        prompt: str,
        csv_path: str | None,
        model: str,
        *,
        width: int,
        height: int,
        style_hint: str,
        count: int = 8,
        language: str = "en",
        parent=None,
        error_notifier=None,
    ):
        super().__init__(parent)
        self.prompt = prompt
        self.csv_path = csv_path
        self.model = model
        self.width = width
        self.height = height
        self.style_hint = style_hint
        self.count = count
        self.language = ensure_language(language)
        self.error_notifier = error_notifier
        self._closing = False

        self.strings: dict = {}
        self.preview_data: List[dict | None] = [None] * count
        self.worker_thread: QThread | None = None
        self.worker: PreviewGeneratorWorker | None = None

        self._setup_ui()
        self.set_language(self.language)
        self._start_generation(count)

    def _setup_ui(self):
        self.setMinimumWidth(820)
        root_layout = QVBoxLayout()

        self.regenerate_top = QPushButton()
        self.regenerate_top.clicked.connect(self.regenerate_unselected)
        root_layout.addWidget(self.regenerate_top)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        container = QWidget()
        self.grid = QGridLayout()
        self.items: List[PreviewItem] = []

        columns = 4
        for idx in range(self.count):
            item = PreviewItem(like_label="")
            row, col = divmod(idx, columns)
            self.grid.addWidget(item, row, col)
            self.items.append(item)

        container.setLayout(self.grid)
        scroll_area.setWidget(container)
        root_layout.addWidget(scroll_area)

        actions_layout = QHBoxLayout()
        self.apply_button = QPushButton()
        self.apply_button.clicked.connect(self.apply_selection)
        self.regenerate_bottom = QPushButton()
        self.regenerate_bottom.clicked.connect(self.regenerate_unselected)
        actions_layout.addWidget(self.apply_button)
        actions_layout.addWidget(self.regenerate_bottom)
        actions_layout.addStretch(1)
        root_layout.addLayout(actions_layout)

        self.setLayout(root_layout)

    def set_language(self, language: str):
        language = ensure_language(language)
        self.language = language
        strings = get_section(language, "preview_gen")
        self.strings = strings
        self.setWindowTitle(strings.get("title", "Preview Gen"))
        like_label = strings.get("like_label", "Like")
        for item in self.items:
            item.checkbox.setText(like_label)
        self.regenerate_top.setText(strings.get("regenerate", "Regenerate"))
        self.regenerate_bottom.setText(strings.get("regenerate", "Regenerate"))
        self.apply_button.setText(strings.get("apply", "Use selected"))

    def _start_generation(self, count: int, target_indices: List[int] | None = None):
        if count <= 0:
            return
        self._set_controls_enabled(False)
        self.worker_thread = QThread()
        self.worker = PreviewGeneratorWorker(
            self.prompt,
            self.csv_path,
            self.model,
            self.width,
            self.height,
            self.style_hint,
            count,
            self.language,
            row_indices=target_indices,
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(
            lambda previews: self._previews_finished(previews, target_indices)
        )
        self.worker.failed.connect(self._previews_failed)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def _previews_finished(self, previews: list, target_indices: List[int] | None):
        indices = target_indices or list(range(len(self.preview_data)))
        for preview, idx in zip(previews, indices):
            self.preview_data[idx] = preview
            if idx < len(self.items):
                self.items[idx].set_preview(preview)
        self._set_controls_enabled(True)

    def _previews_failed(self, message: str):
        self._emit_error(self.strings.get("error_title", "Error"), message, level="error")
        self._set_controls_enabled(True)

    def regenerate_unselected(self):
        target_indices = [idx for idx, item in enumerate(self.items) if not item.checkbox.isChecked()]
        self._start_generation(len(target_indices), target_indices)

    def apply_selection(self):
        if self._closing:
            return
        self._closing = True
        selected = [data for data, item in zip(self.preview_data, self.items) if item.checkbox.isChecked() and data]
        if not selected:
            selected = [data for data in self.preview_data if data]
        self.previewsSelected.emit(selected)
        parent = self.parent()
        if isinstance(parent, QTabWidget):
            index = parent.indexOf(self)
            if index != -1:
                parent.removeTab(index)
        self.deleteLater()

    def _set_controls_enabled(self, enabled: bool):
        self.regenerate_top.setEnabled(enabled)
        self.regenerate_bottom.setEnabled(enabled)
        self.apply_button.setEnabled(enabled)

    def _emit_error(self, title: str, message: str, level: str = "error"):
        if self.error_notifier:
            self.error_notifier.emit_error(title, message, level)
