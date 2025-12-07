import os
import threading

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ai.app_ai import STYLE_HINT, finalize_preview, generate_ai_images
from ai.tools.generator import AVAILABLE_MODELS, DEFAULT_NEGATIVE_PROMPT
from ui.preview_window import PreviewGenWindow
from ui.locales import ensure_language, format_message, get_section


class GenerationWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    def __init__(
        self,
        prompt: str,
        csv_path: str | None,
        model: str,
        count: int,
        width: int,
        height: int,
        style_hint: str,
        negative_prompt: str,
        abort_event: threading.Event,
    ):
        super().__init__()
        self.prompt = prompt
        self.csv_path = csv_path
        self.model = model
        self.count = count
        self.width = width
        self.height = height
        self.style_hint = style_hint
        self.negative_prompt = negative_prompt
        self.abort_event = abort_event

    def run(self):
        try:
            images = generate_ai_images(
                self.prompt,
                self.csv_path,
                self.model,
                self.count,
                self.width,
                self.height,
                self.abort_event.is_set,
                style_hint=self.style_hint,
                negative_prompt=self.negative_prompt,
            )
            self.finished.emit(images)
        except Exception as e:
            self.failed.emit(str(e))


class FinalizationWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, previews: list[dict], abort_event: threading.Event):
        super().__init__()
        self.previews = previews
        self.abort_event = abort_event

    def run(self):
        try:
            results = []
            for idx, preview in enumerate(self.previews):
                if self.abort_event.is_set():
                    break
                path = finalize_preview(preview, steps=40)
                results.append(path)
            self.finished.emit(results)
        except Exception as e:
            self.failed.emit(str(e))


class AiGeneratorTab(QWidget):
    imagesGenerated = Signal(list)

    def __init__(self, parent=None, error_notifier=None):
        super().__init__(parent)
        self.error_notifier = error_notifier

        self.language = ensure_language("en")
        self.strings: dict = {}

        self.generated_images: list[str] = []
        self.csv_path: str | None = None
        self.abort_event: threading.Event | None = None
        self.worker: GenerationWorker | None = None
        self.worker_thread: QThread | None = None
        self.preview_window: PreviewGenWindow | None = None
        self.previewed_images: list[dict] = []

        layout = QVBoxLayout()

        # Prompt
        self.prompt_edit = QTextEdit()
        self.prompt_label = QLabel()
        layout.addWidget(self.prompt_label)
        layout.addWidget(self.prompt_edit)

        # Negative prompt
        self.negative_prompt_label = QLabel()
        layout.addWidget(self.negative_prompt_label)
        self.negative_prompt_edit = QTextEdit()
        self.negative_prompt_edit.setPlainText(DEFAULT_NEGATIVE_PROMPT)
        layout.addWidget(self.negative_prompt_edit)

        # Style hint (editable)
        self.style_label = QLabel()
        layout.addWidget(self.style_label)
        self.style_hint_edit = QTextEdit()
        self.style_hint_edit.setPlainText(STYLE_HINT)
        layout.addWidget(self.style_hint_edit)

        # CSV/JSON loader (optional personalization)
        self.csv_button = QPushButton()
        self.csv_button.clicked.connect(self.load_csv)
        layout.addWidget(self.csv_button)

        # Count
        self.count_edit = QLineEdit("1")
        self.count_label = QLabel()
        layout.addWidget(self.count_label)
        layout.addWidget(self.count_edit)

        # Dimensions
        self.dimensions_label = QLabel()
        layout.addWidget(self.dimensions_label)
        self.dimension_combo = QComboBox()
        self.dimension_options = [
            (500, 700, 200),
            (448, 696, 200),
            (552, 864, 250),
            (664, 1040, 300),
        ]
        self._populate_dimensions()
        layout.addWidget(self.dimension_combo)

        # Model name
        self.model_label = QLabel()
        layout.addWidget(self.model_label)
        self.model_combo = QComboBox()
        self.model_combo.addItems(list(AVAILABLE_MODELS.keys()))
        layout.addWidget(self.model_combo)

        # Generate buttons
        buttons_layout = QHBoxLayout()
        self.generate_button = QPushButton()
        self.generate_button.clicked.connect(self.generate_ai)
        buttons_layout.addWidget(self.generate_button)

        self.preview_button = QPushButton()
        self.preview_button.clicked.connect(self.open_preview_window)
        buttons_layout.addWidget(self.preview_button)
        buttons_layout.addStretch(1)
        layout.addLayout(buttons_layout)

        # Abort button
        self.abort_button = QPushButton()
        self.abort_button.setEnabled(False)
        self.abort_button.clicked.connect(self.abort_generation)
        layout.addWidget(self.abort_button)

        # Preview
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.preview_label)

        self.setLayout(layout)

        self.set_language(self.language)

        QTimer.singleShot(0, lambda: self.open_preview_window(auto_start=False))

    def gather_settings(self) -> dict:
        width, height = self._get_selected_dimensions()
        return {
            "prompt": self.prompt_edit.toPlainText(),
            "negative_prompt": self.negative_prompt_edit.toPlainText(),
            "style_hint": self.style_hint_edit.toPlainText(),
            "count": self.count_edit.text(),
            "dimensions": [width, height],
            "model": self.model_combo.currentText(),
            "csv_path": self.csv_path,
        }

    def apply_settings(self, settings: dict):
        prompt = settings.get("prompt")
        if prompt is not None:
            self.prompt_edit.setPlainText(str(prompt))

        negative_prompt = settings.get("negative_prompt")
        if negative_prompt is not None:
            self.negative_prompt_edit.setPlainText(str(negative_prompt))

        style_hint = settings.get("style_hint")
        if style_hint is not None:
            self.style_hint_edit.setPlainText(str(style_hint))

        count = settings.get("count")
        if count is not None:
            self.count_edit.setText(str(count))

        dimensions = settings.get("dimensions") or []
        if isinstance(dimensions, (list, tuple)) and len(dimensions) == 2:
            try:
                width, height = int(dimensions[0]), int(dimensions[1])
                for idx, (opt_width, opt_height, _) in enumerate(self.dimension_options):
                    if (opt_width, opt_height) == (width, height):
                        self.dimension_combo.setCurrentIndex(idx)
                        break
            except Exception:
                pass

        model = settings.get("model")
        if model and model in [self.model_combo.itemText(i) for i in range(self.model_combo.count())]:
            self.model_combo.setCurrentText(model)

        csv_path = settings.get("csv_path")
        if csv_path:
            self.csv_path = str(csv_path)
            self.csv_button.setText(
                format_message(
                    self.strings,
                    "data_loaded",
                    name=os.path.basename(self.csv_path),
                )
            )

    def set_language(self, language: str):
        language = ensure_language(language)
        self.language = language
        strings = get_section(language, "ai_generator")
        self.strings = strings
        self.prompt_label.setText(strings.get("prompt", ""))
        self.negative_prompt_label.setText(strings.get("negative_prompt", ""))
        self.style_label.setText(strings.get("style_hint", ""))
        self.csv_button.setText(strings.get("load_data", ""))
        self.count_label.setText(strings.get("count", ""))
        self.dimensions_label.setText(strings.get("dimensions", ""))
        self.model_label.setText(strings.get("model_label", strings.get("model", "")))
        self.generate_button.setText(strings.get("generate_button", ""))
        self.preview_button.setText(strings.get("generate_previews_button", ""))
        self.abort_button.setText(strings.get("abort_button", strings.get("abort", "")))
        no_image = strings.get("no_image", "")
        if not self.preview_label.text() or self.preview_label.text() in (
            get_section("en", "ai_generator").get("no_image", ""),
            get_section("uk", "ai_generator").get("no_image", ""),
        ):
            self.preview_label.setText(no_image)
        self._populate_dimensions(strings)

    def load_csv(self):
        start_dir = "config" if os.path.isdir("config") else ""
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.strings.get("open_dialog", ""),
            start_dir,
            "CSV/JSON (*.csv *.json)",
        )
        if path:
            self.csv_path = path
            self.csv_button.setText(
                format_message(
                    self.strings,
                    "data_loaded",
                    name=os.path.basename(path),
                )
            )

    def open_preview_window(self, auto_start: bool = True):
        prompt = self.prompt_edit.toPlainText()
        style_hint = self.style_hint_edit.toPlainText().strip() or STYLE_HINT
        negative_prompt = self.negative_prompt_edit.toPlainText().strip() or DEFAULT_NEGATIVE_PROMPT
        model = self.model_combo.currentText()
        width, height = self._get_selected_dimensions()

        try:
            desired_count = int(self.count_edit.text())
        except Exception:
            self._emit_error(
                self.strings.get("count_error_title", ""),
                self.strings.get("count_error", ""),
                level="warning",
            )
            return
        desired_count = max(desired_count, 1)

        tab_widget = self._get_tab_widget()
        if not tab_widget:
            self._emit_error(
                self.strings.get("fail_title", ""),
                self.strings.get("preview_tab_error", ""),
                level="error",
            )
            return

        if self.preview_window and self.preview_window.count != desired_count:
            existing_index = tab_widget.indexOf(self.preview_window)
            if existing_index != -1:
                tab_widget.removeTab(existing_index)
            self.preview_window.deleteLater()
            self.preview_window = None

        if not self.preview_window:
            self.preview_window = PreviewGenWindow(
                prompt,
                self.csv_path,
                model,
                width=width,
                height=height,
                style_hint=style_hint,
                negative_prompt=negative_prompt,
                count=desired_count,
                language=self.language,
                error_notifier=self.error_notifier,
                parent=tab_widget,
                auto_start=auto_start,
            )
            self.preview_window.previewsSelected.connect(self._store_previews)
        else:
            self.preview_window.refresh_generation(
                prompt,
                self.csv_path,
                model,
                width,
                height,
                style_hint,
                negative_prompt=negative_prompt,
                language=self.language,
                auto_start=auto_start,
            )

        tab_title = get_section(self.language, "tabs").get("preview_gen", "Preview")
        existing_index = tab_widget.indexOf(self.preview_window)
        if existing_index == -1:
            tab_widget.addTab(self.preview_window, tab_title)
        else:
            tab_widget.setTabText(existing_index, tab_title)
        tab_widget.setCurrentWidget(self.preview_window)

    def _get_tab_widget(self) -> QTabWidget | None:
        current = self.parent()
        while current:
            if isinstance(current, QTabWidget):
                return current
            current = current.parent()
        window = self.window()
        if hasattr(window, "centralWidget"):
            central = window.centralWidget()
            if isinstance(central, QTabWidget):
                return central
        return None

    def generate_ai(self):
        prompt = self.prompt_edit.toPlainText()
        style_hint = self.style_hint_edit.toPlainText().strip() or STYLE_HINT
        negative_prompt = self.negative_prompt_edit.toPlainText().strip() or DEFAULT_NEGATIVE_PROMPT
        model = self.model_combo.currentText()

        try:
            count = int(self.count_edit.text())
        except Exception:
            self._emit_error(
                self.strings.get("count_error_title", ""),
                self.strings.get("count_error", ""),
                level="warning",
            )
            return

        width, height = self._get_selected_dimensions()

        if self.previewed_images:
            self.abort_event = threading.Event()
            self._set_generation_controls(enabled=False)

            self.worker_thread = QThread()
            self.worker = FinalizationWorker(self.previewed_images, self.abort_event)
            self.worker.moveToThread(self.worker_thread)
            self.worker_thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.generation_finished)
            self.worker.failed.connect(self.generation_failed)
            self.worker.finished.connect(self.worker_thread.quit)
            self.worker.failed.connect(self.worker_thread.quit)
            self.worker_thread.finished.connect(self.worker.deleteLater)
            self.worker_thread.finished.connect(self.worker_thread.deleteLater)
            self.worker_thread.start()
            return

        self.abort_event = threading.Event()
        self._set_generation_controls(enabled=False)

        self.worker_thread = QThread()
        self.worker = GenerationWorker(
            prompt,
            self.csv_path,
            model,
            count,
            width,
            height,
            style_hint,
            negative_prompt,
            self.abort_event
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.generation_finished)
        self.worker.failed.connect(self.generation_failed)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def generation_finished(self, images):
        self.generated_images = images
        self.imagesGenerated.emit(images)

        if images:
            pixmap = QPixmap(images[0])
            self.preview_label.setPixmap(pixmap.scaled(256, 256, Qt.KeepAspectRatio))

        if self.abort_event and self.abort_event.is_set():
            self._emit_error(
                self.strings.get("aborted_title", ""),
                format_message(self.strings, "aborted_message", count=len(images)),
                level="info",
            )
        else:
            self._emit_error(
                self.strings.get("done_title", ""),
                format_message(self.strings, "done_message", count=len(images)),
                level="info",
            )
        self._set_generation_controls(enabled=True)
        self._reset_worker_state()

    def _store_previews(self, previews: list[dict]):
        self.previewed_images = previews or []
        if self.previewed_images:
            first_path = self.previewed_images[0].get("path")
            if first_path and os.path.isfile(first_path):
                pixmap = QPixmap(first_path)
                self.preview_label.setPixmap(
                    pixmap.scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
        # Keep preview tab active for future regenerations

    def generation_failed(self, message: str):
        self._emit_error(
            self.strings.get("fail_title", ""),
            message,
            level="error",
        )
        self._set_generation_controls(enabled=True)
        self._reset_worker_state()

    def abort_generation(self):
        if self.abort_event:
            self.abort_event.set()
        self.abort_button.setEnabled(False)

    def _set_generation_controls(self, enabled: bool):
        self.generate_button.setEnabled(enabled)
        self.preview_button.setEnabled(enabled)
        self.csv_button.setEnabled(enabled)
        self.abort_button.setEnabled(not enabled)

    def _reset_worker_state(self):
        self.worker = None
        self.worker_thread = None
        self.abort_event = None

    def get_generated_images(self) -> list[str]:
        return self.generated_images

    def _emit_error(self, title: str, message: str, level: str = "error"):
        if self.error_notifier:
            self.error_notifier.emit_error(title, message, level)

    def _populate_dimensions(self, strings: dict | None = None):
        strings = strings or self.strings or {}
        current = self._get_selected_dimensions()
        selection_label = self.dimension_combo.currentText()
        self.dimension_combo.clear()

        labels = strings.get("dimension_labels", [])
        for idx, (width, height, dpi) in enumerate(self.dimension_options):
            label = labels[idx] if idx < len(labels) else f"{width} × {height} px ({dpi} DPI)"
            self.dimension_combo.addItem(label)

        if current:
            for idx, (width, height, _) in enumerate(self.dimension_options):
                if (width, height) == current:
                    self.dimension_combo.setCurrentIndex(idx)
                    break
        elif selection_label:
            for idx, label in enumerate(labels):
                if selection_label == label:
                    self.dimension_combo.setCurrentIndex(idx)
                    break

    def _get_selected_dimensions(self):
        index = self.dimension_combo.currentIndex()
        if 0 <= index < len(self.dimension_options):
            width, height, _ = self.dimension_options[index]
            return width, height
        width, height, _ = self.dimension_options[0]
        return width, height


# Late imports to avoid circular dependencies in type checkers
from PySide6.QtWidgets import QFileDialog  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
