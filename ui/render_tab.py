import os
import tempfile
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from renderer.core.json_loader import load_template
from renderer.core.paths import ABSOLUTE_PATH
from renderer.core.psd_importer import PsdImporter
from renderer.core.renderer import CardRenderer
from renderer.widgets.drag_canvas import DragCanvas
from renderer.widgets.property_panel import PropertyPanel
from ui.locales import ensure_language, format_message, get_section


class RenderTab(QWidget):
    cardsRendered = Signal(list)

    def __init__(self, get_generated_images, get_export_dir, parent=None, error_notifier=None):
        super().__init__(parent)
        self.get_generated_images = get_generated_images
        self.get_export_dir = get_export_dir
        self.error_notifier = error_notifier

        self.language = ensure_language("en")
        self.strings: dict = {}

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

        # Button: import PSD layout
        self.import_psd_button = QPushButton()
        self.import_psd_button.clicked.connect(self.import_psd)
        right.addWidget(self.import_psd_button)

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

    def import_psd(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.strings.get("import_psd_title", ""),
            "",
            "PSD files (*.psd)",
        )
        if not path:
            return

        try:
            importer = PsdImporter(path)
            result = importer.load()
            cache_dir = Path(tempfile.gettempdir()) / "ls_gen" / "psd"
            cache_dir.mkdir(parents=True, exist_ok=True)

            composite_path = cache_dir / f"{Path(path).stem}.png"
            result.save_composite(composite_path)
            layers_dir = cache_dir / f"{Path(path).stem}_layers"
            exported_layers = result.export_layers(layers_dir)
        except Exception as exc:
            self._emit_error(
                self.strings.get("error_title", ""),
                format_message(self.strings, "import_psd_failed", error=exc),
                level="error",
            )
            return

        self.scene.set_art_pixmap(str(composite_path))
        self.current_art = str(composite_path)
        self._emit_error(
            self.strings.get("import_psd_done_title", ""),
            format_message(
                self.strings,
                "import_psd_done",
                path=composite_path,
                layers=len(exported_layers),
            ),
            level="info",
        )

    def apply_ai_to_card(self):
        generated_images = self.get_generated_images()
        if not generated_images:
            self._emit_error(
                self.strings.get("no_images_title", ""),
                self.strings.get("no_images_message", ""),
                level="warning",
            )
            return

        first_img = generated_images[0]
        self.scene.set_art_pixmap(first_img)
        self.current_art = first_img

    def render_card(self):
        if not self.current_art:
            self._emit_error(
                self.strings.get("error_title", ""),
                self.strings.get("apply_first", ""),
                level="warning",
            )
            return

        export_dir = (self.get_export_dir() or "export").strip() or "export"
        os.makedirs(export_dir, exist_ok=True)

        # minimal card data
        card_data = {
            "img": self.current_art,
            "title": self.strings.get("default_title", "Generated Unit"),
            "description": self.strings.get("default_desc", "AI-generated card"),
            "atk": 3,
            "def": 2,
            "stb": 1
        }

        renderer = CardRenderer(self.template)
        img = renderer.render(card_data)

        save_path = os.path.join(export_dir, "rendered_card.png")
        img.save(save_path)

        self._emit_error(
            self.strings.get("done_title", ""),
            format_message(self.strings, "done_message", path=save_path),
            level="info",
        )

        self.rendered_cards = [save_path]
        self.cardsRendered.emit(self.rendered_cards)

    def get_rendered_cards(self) -> list[str]:
        return self.rendered_cards

    def set_language(self, language: str):
        language = ensure_language(language)
        self.language = language
        strings = get_section(language, "render_tab")
        self.strings = strings
        self.import_psd_button.setText(strings.get("import_psd", "Import PSD"))
        self.apply_ai_button.setText(strings.get("apply_ai", ""))
        self.render_button.setText(strings.get("render_card", ""))

    def _emit_error(self, title: str, message: str, level: str = "error"):
        if self.error_notifier:
            self.error_notifier.emit_error(title, message, level)
