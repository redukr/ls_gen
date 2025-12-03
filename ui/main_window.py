from PySide6.QtWidgets import (
    QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QTextEdit, QFileDialog, QTabWidget, QMessageBox,
    QTableWidget, QTableWidgetItem
)
from PySide6.QtGui import QPixmap, QGuiApplication, QKeySequence
from PySide6.QtCore import Qt, QObject, QThread, Signal
import json
import os
import threading
import csv

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
from renderer.core.pdf_exporter import export_pdf_from_list

from PySide6.QtWidgets import QComboBox

from transformers import pipeline


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


class OfflineTranslator:
    def __init__(self, model_dir: str = "models/opus-mt-uk-en"):
        self.model_dir = os.path.abspath(model_dir)
        self._translator = None

    def _load_translator(self):
        if self._translator is None:
            os.makedirs(self.model_dir, exist_ok=True)
            self._translator = pipeline(
                "translation",
                model="Helsinki-NLP/opus-mt-uk-en",
                tokenizer="Helsinki-NLP/opus-mt-uk-en",
                cache_dir=self.model_dir,
            )

    def translate(self, text: str) -> str:
        if not text or not text.strip():
            return ""
        self._load_translator()
        result = self._translator(text, max_length=512)
        return result[0]["translation_text"] if result else ""


class DataTableWidget(QTableWidget):
    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            self.copy_selection()
            return
        if event.matches(QKeySequence.Paste):
            self.paste_selection()
            return
        super().keyPressEvent(event)

    def copy_selection(self):
        ranges = self.selectedRanges()
        if not ranges:
            return
        selected = ranges[0]
        rows = []
        for row in range(selected.topRow(), selected.bottomRow() + 1):
            values = []
            for col in range(selected.leftColumn(), selected.rightColumn() + 1):
                item = self.item(row, col)
                values.append(item.text() if item else "")
            rows.append("\t".join(values))
        QGuiApplication.clipboard().setText("\n".join(rows))

    def paste_selection(self):
        start_row = self.currentRow()
        start_col = self.currentColumn()
        if start_row < 0 or start_col < 0:
            return
        text = QGuiApplication.clipboard().text()
        lines = text.splitlines()
        required_rows = start_row + len(lines)
        if required_rows > self.rowCount():
            self.setRowCount(required_rows)
        column_limit = self.columnCount()
        for r_offset, line in enumerate(lines):
            cells = line.split("\t")
            for c_offset, cell in enumerate(cells):
                target_col = start_col + c_offset
                if target_col >= column_limit:
                    break
                self.setItem(start_row + r_offset, target_col, QTableWidgetItem(cell))


class DataEditorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.translator = OfflineTranslator()
        self.headers = []
        self.current_path = None
        self.updating = False

        layout = QVBoxLayout()
        button_row = QHBoxLayout()
        self.load_btn = QPushButton("Load CSV/JSON")
        self.save_btn = QPushButton("Save CSV/JSON")
        button_row.addWidget(self.load_btn)
        button_row.addWidget(self.save_btn)
        layout.addLayout(button_row)

        self.table = DataTableWidget()
        self.table.setSortingEnabled(True)
        self.table.cellChanged.connect(self.on_cell_changed)
        layout.addWidget(self.table)

        self.setLayout(layout)

        self.load_btn.clicked.connect(self.load_file)
        self.save_btn.clicked.connect(self.save_file)

    def load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open CSV or JSON", "config", "CSV/JSON (*.csv *.json)")
        if not path:
            return
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext == ".csv":
                with open(path, newline='', encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    data = list(reader)
            elif ext == ".json":
                with open(path, encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        data = list(loaded.values())
                    else:
                        data = loaded
            else:
                QMessageBox.warning(self, "Unsupported", "Only CSV or JSON files are supported")
                return
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to load file: {exc}")
            return

        if not isinstance(data, list):
            QMessageBox.warning(self, "Error", "Loaded data is not a list of rows")
            return

        self.current_path = path
        self._populate_table(data)

    def save_file(self):
        if not self.headers:
            QMessageBox.warning(self, "No data", "Nothing to save")
            return
        default_dir = os.path.dirname(self.current_path) if self.current_path else "config"
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV or JSON", default_dir, "CSV/JSON (*.csv *.json)")
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        data = self._gather_rows()
        try:
            if ext == ".csv" or not ext:
                if not ext:
                    path += ".csv"
                with open(path, "w", newline='', encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=self.headers)
                    writer.writeheader()
                    writer.writerows(data)
            elif ext == ".json":
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                QMessageBox.warning(self, "Unsupported", "Please use .csv or .json extension")
                return
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to save file: {exc}")
            return
        QMessageBox.information(self, "Saved", f"Data saved to {path}")

    def _populate_table(self, data):
        self.updating = True
        self.headers = self._collect_headers(data)
        self._ensure_name_en()
        self.table.setSortingEnabled(False)
        self.table.clear()
        self.table.setColumnCount(len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)
        self.table.setRowCount(len(data))

        for row_index, row in enumerate(data):
            for col_index, header in enumerate(self.headers):
                value = row.get(header, "") if isinstance(row, dict) else ""
                item = QTableWidgetItem(str(value))
                self.table.setItem(row_index, col_index, item)
                if header == "name_en" and str(value).strip():
                    item.setData(Qt.UserRole, True)

        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()
        self.updating = False
        self._auto_translate_missing()

    def _collect_headers(self, data):
        headers = []
        for row in data:
            if isinstance(row, dict):
                for key in row.keys():
                    if key not in headers:
                        headers.append(key)
        return headers

    def _ensure_name_en(self):
        if "name_en" not in self.headers:
            self.headers.append("name_en")
        if "name" not in self.headers:
            self.headers.insert(0, "name")

    def _gather_rows(self):
        rows = []
        for row in range(self.table.rowCount()):
            record = {}
            for col, header in enumerate(self.headers):
                item = self.table.item(row, col)
                record[header] = item.text() if item else ""
            rows.append(record)
        return rows

    def on_cell_changed(self, row, column):
        if self.updating or column >= len(self.headers):
            return
        header = self.headers[column]
        if header == "name_en":
            item = self.table.item(row, column)
            if item:
                item.setData(Qt.UserRole, True)
                item.setData(Qt.UserRole + 1, "")
            self.table.resizeColumnsToContents()
            return
        if header == "name":
            self._update_translation_for_row(row)
        self.table.resizeColumnsToContents()

    def _auto_translate_missing(self):
        if "name" not in self.headers or "name_en" not in self.headers:
            return
        for row in range(self.table.rowCount()):
            target_item = self.table.item(row, self.headers.index("name_en"))
            if target_item and target_item.data(Qt.UserRole):
                continue
            if target_item and target_item.text().strip():
                continue
            self._update_translation_for_row(row)

    def _update_translation_for_row(self, row):
        name_en_index = self.headers.index("name_en")
        name_item = self.table.item(row, self.headers.index("name"))
        target_item = self.table.item(row, name_en_index)
        current_name = name_item.text() if name_item else ""
        current_target = target_item.text() if target_item else ""
        manual = bool(target_item and target_item.data(Qt.UserRole))
        auto_value = target_item.data(Qt.UserRole + 1) if target_item else ""
        if manual and current_target:
            return
        if not manual and current_target and current_target != auto_value:
            if target_item:
                target_item.setData(Qt.UserRole, True)
            return
        translation = self.translator.translate(current_name)
        if translation:
            self.updating = True
            new_item = target_item or QTableWidgetItem()
            new_item.setText(translation)
            new_item.setData(Qt.UserRole, False)
            new_item.setData(Qt.UserRole + 1, translation)
            self.table.setItem(row, name_en_index, new_item)
            self.table.resizeColumnsToContents()
            self.updating = False


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
        self.tab_data = QWidget()

        self.tabs.addTab(self.tab_ai, "AI Generator")
        self.tabs.addTab(self.tab_render, "Card Renderer")
        self.tabs.addTab(self.tab_export, "Export")
        self.tabs.addTab(self.tab_data, "Data Editor")

        # setup
        self.setup_ai_tab()
        self.setup_render_tab()
        self.setup_export_tab()
        self.setup_data_tab()

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

    # --------------------------
    # TAB 4: DATA EDITOR
    # --------------------------
    def setup_data_tab(self):
        layout = QVBoxLayout()
        self.data_editor = DataEditorWidget()
        layout.addWidget(self.data_editor)
        self.tab_data.setLayout(layout)
