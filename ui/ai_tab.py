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

        self.generated_images: list[str] = []
        self.csv_path: str | None = None
        self.abort_event: threading.Event | None = None
        self.worker: GenerationWorker | None = None
        self.worker_thread: QThread | None = None

        layout = QVBoxLayout()

        # Prompt
        self.prompt_edit = QTextEdit()
        layout.addWidget(QLabel("Prompt:"))
        layout.addWidget(self.prompt_edit)

        # Style hint (editable)
        layout.addWidget(QLabel("Style hint:"))
        self.style_hint_edit = QTextEdit()
        self.style_hint_edit.setPlainText(STYLE_HINT)
        layout.addWidget(self.style_hint_edit)

        # CSV/JSON loader (optional personalization)
        self.csv_button = QPushButton("Load CSV/JSON")
        self.csv_button.clicked.connect(self.load_csv)
        layout.addWidget(self.csv_button)

        # Count
        self.count_edit = QLineEdit("1")
        layout.addWidget(QLabel("Count:"))
        layout.addWidget(self.count_edit)

        # Dimensions
        layout.addWidget(QLabel("Dimensions:"))
        self.dimension_combo = QComboBox()
        self.dimension_options = {
            "448 × 696 px (200 DPI)": (448, 696),
            "552 × 864 px (250 DPI)": (552, 864),
            "664 × 1040 px (300 DPI)": (664, 1040),
        }
        self.dimension_combo.addItems(self.dimension_options.keys())
        layout.addWidget(self.dimension_combo)

        # Model name
        layout.addWidget(QLabel("Model name:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "RealVisXL (SDXL)",
            "SDXL Base 1.0"
        ])
        layout.addWidget(self.model_combo)

        # Generate button
        self.generate_button = QPushButton("Generate Images")
        self.generate_button.clicked.connect(self.generate_ai)
        layout.addWidget(self.generate_button)

        # Abort button
        self.abort_button = QPushButton("Abort")
        self.abort_button.setEnabled(False)
        self.abort_button.clicked.connect(self.abort_generation)
        layout.addWidget(self.abort_button)

        # Preview
        self.preview_label = QLabel("No Image")
        self.preview_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.preview_label)

        self.setLayout(layout)

    def load_csv(self):
        start_dir = "config" if os.path.isdir("config") else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV or JSON", start_dir, "CSV/JSON (*.csv *.json)")
        if path:
            self.csv_path = path
            self.csv_button.setText(f"Data Loaded: {os.path.basename(path)}")

    def generate_ai(self):
        prompt = self.prompt_edit.toPlainText()
        style_hint = self.style_hint_edit.toPlainText().strip() or STYLE_HINT
        model = self.model_combo.currentText()

        try:
            count = int(self.count_edit.text())
        except Exception:
            QMessageBox.warning(self, "Error", "Count must be integer")
            return

        width, height = self.dimension_options.get(
            self.dimension_combo.currentText(),
            (768, 1088)
        )

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
            QMessageBox.information(self, "Aborted", f"Generation aborted after {len(images)} images")
        else:
            QMessageBox.information(self, "Done", f"Generated {len(images)} images")
        self._set_generation_controls(enabled=True)
        self._reset_worker_state()

    def generation_failed(self, message: str):
        QMessageBox.critical(self, "Generation failed", message)
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


# Late imports to avoid circular dependencies in type checkers
from PySide6.QtWidgets import QFileDialog  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
