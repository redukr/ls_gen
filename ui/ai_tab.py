import os
import threading

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ai.app_ai import generate_ai_images, STYLE_HINT
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
            )
            self.finished.emit(images)
        except Exception as e:
            self.failed.emit(str(e))


class AiGeneratorTab(QWidget):
    imagesGenerated = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.language = ensure_language("en")
        self.strings: dict = {}

        self.generated_images: list[str] = []
        self.csv_path: str | None = None
        self.abort_event: threading.Event | None = None
        self.worker: GenerationWorker | None = None
        self.worker_thread: QThread | None = None

        layout = QVBoxLayout()

        # Prompt
        self.prompt_edit = QTextEdit()
        self.prompt_label = QLabel()
        layout.addWidget(self.prompt_label)
        layout.addWidget(self.prompt_edit)

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
        self.model_combo.addItems([
            "RealVisXL (SDXL)",
            "SDXL Base 1.0"
        ])
        layout.addWidget(self.model_combo)

        # Generate button
        self.generate_button = QPushButton()
        self.generate_button.clicked.connect(self.generate_ai)
        layout.addWidget(self.generate_button)

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

    def set_language(self, language: str):
        language = ensure_language(language)
        self.language = language
        strings = get_section(language, "ai_generator")
        self.strings = strings
        self.prompt_label.setText(strings.get("prompt", ""))
        self.style_label.setText(strings.get("style_hint", ""))
        self.csv_button.setText(strings.get("load_data", ""))
        self.count_label.setText(strings.get("count", ""))
        self.dimensions_label.setText(strings.get("dimensions", ""))
        self.model_label.setText(strings.get("model_label", strings.get("model", "")))
        self.generate_button.setText(strings.get("generate_button", ""))
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

    def generate_ai(self):
        prompt = self.prompt_edit.toPlainText()
        style_hint = self.style_hint_edit.toPlainText().strip() or STYLE_HINT
        model = self.model_combo.currentText()

        try:
            count = int(self.count_edit.text())
        except Exception:
            QMessageBox.warning(
                self,
                self.strings.get("count_error_title", ""),
                self.strings.get("count_error", ""),
            )
            return

        width, height = self._get_selected_dimensions()

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
            QMessageBox.information(
                self,
                self.strings.get("aborted_title", ""),
                format_message(self.strings, "aborted_message", count=len(images)),
            )
        else:
            QMessageBox.information(
                self,
                self.strings.get("done_title", ""),
                format_message(self.strings, "done_message", count=len(images)),
            )
        self._set_generation_controls(enabled=True)
        self._reset_worker_state()

    def generation_failed(self, message: str):
        QMessageBox.critical(
            self,
            self.strings.get("fail_title", ""),
            message,
        )
        self._set_generation_controls(enabled=True)
        self._reset_worker_state()

    def abort_generation(self):
        if self.abort_event:
            self.abort_event.set()
        self.abort_button.setEnabled(False)

    def _set_generation_controls(self, enabled: bool):
        self.generate_button.setEnabled(enabled)
        self.csv_button.setEnabled(enabled)
        self.abort_button.setEnabled(not enabled)

    def _reset_worker_state(self):
        self.worker = None
        self.worker_thread = None
        self.abort_event = None

    def get_generated_images(self) -> list[str]:
        return self.generated_images

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
