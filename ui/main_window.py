from PySide6.QtWidgets import (
    QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QTextEdit, QFileDialog, QTabWidget, QMessageBox
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
import os

# AI generator
from LS_gen.ai.app_ai import generate_ai_images

# Card Renderer core
from LS_gen.renderer.core.json_loader import load_template
from LS_gen.renderer.core.renderer import CardRenderer
from LS_gen.renderer.core.paths import ABSOLUTE_PATH

# Card Scene (preview)
from LS_gen.renderer.widgets.card_scene_view import CardSceneView

# PDF Exporter
from LS_gen.renderer.core.pdf_exporter import export_pdf


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("LS_gen — AI Generator + Card Renderer")

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

        # CSV loader
        self.csv_path = None
        self.csv_button = QPushButton("Load CSV")
        self.csv_button.clicked.connect(self.load_csv)
        layout.addWidget(self.csv_button)

        # Count
        self.count_edit = QLineEdit("1")
        layout.addWidget(QLabel("Count:"))
        layout.addWidget(self.count_edit)

        # Model name
        self.model_edit = QLineEdit("realvisxl")
        layout.addWidget(QLabel("Model name:"))
        layout.addWidget(self.model_edit)

        # Generate button
        self.generate_button = QPushButton("Generate Images")
        self.generate_button.clicked.connect(self.generate_ai)
        layout.addWidget(self.generate_button)

        # Preview
        self.preview_label = QLabel("No Image")
        self.preview_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.preview_label)

        self.tab_ai.setLayout(layout)

    def load_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select CSV", "", "CSV (*.csv)")
        if path:
            self.csv_path = path
            self.csv_button.setText(f"CSV Loaded: {os.path.basename(path)}")

    def generate_ai(self):
        prompt = self.prompt_edit.toPlainText()
        model = self.model_edit.text()

        try:
            count = int(self.count_edit.text())
        except:
            QMessageBox.warning(self, "Error", "Count must be integer")
            return

        images = generate_ai_images(prompt, self.csv_path, model, count)
        self.generated_images = images

        if images:
            pixmap = QPixmap(images[0])
            self.preview_label.setPixmap(pixmap.scaled(256, 256, Qt.KeepAspectRatio))

        QMessageBox.information(self, "Done", f"Generated {len(images)} images")

    # --------------------------
    # TAB 2: CARD RENDERER
    # --------------------------
    def setup_render_tab(self):
        layout = QHBoxLayout()

        # Card preview scene
        self.scene = CardSceneView()
        layout.addWidget(self.scene)

        # Control panel
        right = QVBoxLayout()

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

        btn = QPushButton("Export deck to PDF")
        btn.clicked.connect(self.export_pdf_deck)
        layout.addWidget(btn)

        self.tab_export.setLayout(layout)

    def export_pdf_deck(self):
        if not hasattr(self, "rendered_cards"):
            QMessageBox.warning(self, "Error", "Render a card first")
            return

        os.makedirs("export", exist_ok=True)

        out = "export/deck.pdf"
        export_pdf(self.rendered_cards, out)

        QMessageBox.information(self, "Done", f"PDF exported: {out}")