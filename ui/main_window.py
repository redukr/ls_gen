from PySide6.QtWidgets import (
    QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QTextEdit, QFileDialog, QTabWidget, QMessageBox
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QObject, QThread, Signal
import os
import threading

# AI generator
from ai.app_ai import generate_ai_images, STYLE_HINT

from renderer.widgets.property_panel import PropertyPanel


# Card Renderer core
from renderer.core.json_loader import load_template
from renderer.core.renderer import CardRenderer
from renderer.core.paths import ABSOLUTE_PATH

# Card Scene (preview)
from renderer.widgets.drag_canvas import DragCanvas

# PDF Exporter
from renderer.core.pdf_exporter import export_pdf

from PySide6.QtWidgets import QComboBox
from PySide6.QtWidgets import QFileDialog


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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("LS_gen — AI Generator + Card Renderer")
        self.setMinimumSize(400, 300)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # tabs
        self.tab_ai = QWidget()
        self.tab_render = QWidget()
        self.tab_export = QWidget()

        self.tabs.addTab(self.tab_ai, "AI Generator")
        self.tabs.addTab(self.tab_render, "Card Renderer")
        self.tabs.addTab(self.tab_export, "Export")

        # setup
        self.setup_ai_tab()
        self.setup_render_tab()
        self.setup_export_tab()

    # --------------------------
    # TAB 1: AI GENERATOR
    # --------------------------
    def setup_ai_tab(self):
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
        self.csv_path = None
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

        self.tab_ai.setLayout(layout)

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
        except:
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

        if images:
            pixmap = QPixmap(images[0])
            self.preview_label.setPixmap(pixmap.scaled(256, 256, Qt.KeepAspectRatio))

        if hasattr(self, "abort_event") and self.abort_event.is_set():
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
        if hasattr(self, "abort_event"):
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

    # --------------------------
    # TAB 2: CARD RENDERER
    # --------------------------
    def setup_render_tab(self):
        layout = QHBoxLayout()

        # Card preview scene
        self.scene = DragCanvas("renderer/templates/template.json")
        layout.addWidget(self.scene)

        # Control panel
        right = QVBoxLayout()
        
        self.property_panel = PropertyPanel()
        right.addWidget(self.property_panel)
        self.scene.itemSelected.connect(self.property_panel.set_item)
        self.property_panel.settingsChanged.connect(self.scene.save_template)
        
        # Load template
        layout_path = ABSOLUTE_PATH("templates/template.json")
        self.template = load_template(layout_path)

        # Button: load AI image into card preview
        self.apply_ai_button = QPushButton("Apply AI Image")
        self.apply_ai_button.clicked.connect(self.apply_ai_to_card)
        right.addWidget(self.apply_ai_button)

        # Button: render final card (PNG)
        self.render_button = QPushButton("Render Card")
        self.render_button.clicked.connect(self.render_card)
        right.addWidget(self.render_button)

        layout.addLayout(right)
        self.tab_render.setLayout(layout)

    def apply_ai_to_card(self):
        if not hasattr(self, "generated_images"):
            QMessageBox.warning(self, "No images", "Please generate AI images first")
            return

        first_img = self.generated_images[0]
        self.scene.set_art_pixmap(first_img)
        self.current_art = first_img

    def render_card(self):
        if not hasattr(self, "current_art"):
            QMessageBox.warning(self, "Error", "Apply AI image first")
            return

        # minimal card data
        card_data = {
            "img": self.current_art,
            "title": "Generated Unit",
            "description": "AI-generated card",
            "atk": 3,
            "def": 2,
            "stb": 1
        }

        renderer = CardRenderer(self.template)
        img = renderer.render(card_data)

        os.makedirs("export", exist_ok=True)
        save_path = "export/rendered_card.png"
        img.save(save_path)

        QMessageBox.information(self, "Done", f"Card saved: {save_path}")

        # store for export
        self.rendered_cards = [save_path]

    # --------------------------
    # TAB 3: EXPORT
    # --------------------------
    def setup_export_tab(self):
        layout = QVBoxLayout()

        self.export_dir = QLineEdit()
        self.export_dir.setPlaceholderText("Select export directory...")
        layout.addWidget(self.export_dir)

        choose_btn = QPushButton("Choose folder")
        choose_btn.clicked.connect(self.choose_export_folder)
        layout.addWidget(choose_btn)

        export_btn = QPushButton("Export deck to PDF")
        export_btn.clicked.connect(self.export_pdf_deck)
        layout.addWidget(export_btn)

        self.tab_export.setLayout(layout)

    def export_pdf_deck(self):
        if not hasattr(self, "rendered_cards"):
            QMessageBox.warning(self, "Error", "Render a card first")
            return

        os.makedirs("export", exist_ok=True)

        export_path = self.export_dir.text().strip()

        if not export_path:
            QMessageBox.warning(self, "Error", "Please choose export directory first")
            return

        out = os.path.join(export_path, "deck.pdf")
        export_pdf_from_list(self.rendered_cards, out)

        QMessageBox.information(self, "Done", f"PDF exported: {out}")
        
    def choose_export_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select export folder")
        if folder:
            self.export_dir.setText(folder)
