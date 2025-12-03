import os

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from renderer.core.json_loader import load_template
from renderer.core.renderer import CardRenderer
from renderer.core.paths import ABSOLUTE_PATH
from renderer.widgets.drag_canvas import DragCanvas
from renderer.widgets.property_panel import PropertyPanel


class RenderTab(QWidget):
    cardsRendered = Signal(list)

    def __init__(self, get_generated_images, get_export_dir, parent=None):
        super().__init__(parent)
        self.get_generated_images = get_generated_images
        self.get_export_dir = get_export_dir

        self.language = "en"
        self.strings = {
            "en": {
                "apply_ai": "Apply AI Image",
                "render_card": "Render Card",
                "no_images_title": "No images",
                "no_images_message": "Please generate AI images first",
                "error_title": "Error",
                "apply_first": "Apply AI image first",
                "default_title": "Generated Unit",
                "default_desc": "AI-generated card",
                "done_title": "Done",
                "done_message": "Card saved: {path}",
            },
            "uk": {
                "apply_ai": "Додати AI-зображення",
                "render_card": "Відрендерити картку",
                "no_images_title": "Немає зображень",
                "no_images_message": "Спочатку згенеруйте AI-зображення",
                "error_title": "Помилка",
                "apply_first": "Спочатку додайте AI-зображення",
                "default_title": "Згенерований юніт",
                "default_desc": "Картка, згенерована ШІ",
                "done_title": "Готово",
                "done_message": "Картку збережено: {path}",
            },
        }

        self.rendered_cards: list[str] = []
        self.current_art: str | None = None

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
        self.apply_ai_button = QPushButton()
        self.apply_ai_button.clicked.connect(self.apply_ai_to_card)
        right.addWidget(self.apply_ai_button)

        # Button: render final card (PNG)
        self.render_button = QPushButton()
        self.render_button.clicked.connect(self.render_card)
        right.addWidget(self.render_button)

        layout.addLayout(right)
        self.setLayout(layout)

        self.set_language(self.language)

    def apply_ai_to_card(self):
        generated_images = self.get_generated_images()
        if not generated_images:
            QMessageBox.warning(
                self,
                self.strings[self.language]["no_images_title"],
                self.strings[self.language]["no_images_message"],
            )
            return

        first_img = generated_images[0]
        self.scene.set_art_pixmap(first_img)
        self.current_art = first_img

    def render_card(self):
        if not self.current_art:
            QMessageBox.warning(
                self,
                self.strings[self.language]["error_title"],
                self.strings[self.language]["apply_first"],
            )
            return

        export_dir = (self.get_export_dir() or "export").strip() or "export"
        os.makedirs(export_dir, exist_ok=True)

        # minimal card data
        card_data = {
            "img": self.current_art,
            "title": self.strings[self.language]["default_title"],
            "description": self.strings[self.language]["default_desc"],
            "atk": 3,
            "def": 2,
            "stb": 1
        }

        renderer = CardRenderer(self.template)
        img = renderer.render(card_data)

        save_path = os.path.join(export_dir, "rendered_card.png")
        img.save(save_path)

        QMessageBox.information(
            self,
            self.strings[self.language]["done_title"],
            self.strings[self.language]["done_message"].format(path=save_path),
        )

        self.rendered_cards = [save_path]
        self.cardsRendered.emit(self.rendered_cards)

    def get_rendered_cards(self) -> list[str]:
        return self.rendered_cards

    def set_language(self, language: str):
        if language not in self.strings:
            return
        self.language = language
        s = self.strings[language]
        self.apply_ai_button.setText(s["apply_ai"])
        self.render_button.setText(s["render_card"])
