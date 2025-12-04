import os

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from renderer.core.pdf_exporter import export_pdf_from_list
from ui.locales import (
    available_languages,
    ensure_language,
    format_message,
    get_section,
)


class ExportTab(QWidget):
    languageChanged = Signal(str)

    def __init__(self, get_rendered_cards, parent=None, error_notifier=None):
        super().__init__(parent)
        self.get_rendered_cards = get_rendered_cards
        self.error_notifier = error_notifier
        self.language = ensure_language("en")
        self.strings: dict = {}
        self.available_languages = available_languages()

        layout = QVBoxLayout()

        self.export_dir = QLineEdit()
        self.export_dir.setPlaceholderText("")
        layout.addWidget(self.export_dir)

        self.choose_btn = QPushButton()
        self.choose_btn.clicked.connect(self.choose_export_folder)
        layout.addWidget(self.choose_btn)

        self.export_btn = QPushButton()
        self.export_btn.clicked.connect(self.export_pdf_deck)
        layout.addWidget(self.export_btn)

        self.language_box = QGroupBox()
        language_layout = QHBoxLayout()
        self.language_buttons: dict[str, QRadioButton] = {}
        for code in sorted(self.available_languages):
            button = QRadioButton()
            button.toggled.connect(lambda checked, code=code: self._on_language_toggle(code, checked))
            self.language_buttons[code] = button
            language_layout.addWidget(button)
        self.language_box.setLayout(language_layout)
        layout.addWidget(self.language_box)

        self.setLayout(layout)
        
    def export_pdf_deck(self):
        rendered_cards = self.get_rendered_cards()
        if not rendered_cards:
            self._emit_error(
                self.strings.get("error_title", ""),
                self.strings.get("render_first", ""),
                level="warning",
            )
            return

        export_path = self.export_dir.text().strip() or "export"
        os.makedirs(export_path, exist_ok=True)

        out = os.path.join(export_path, "deck.pdf")
        export_pdf_from_list(rendered_cards, out)

        self._emit_error(
            self.strings.get("done_title", ""),
            format_message(self.strings, "pdf_exported", path=out),
            level="info",
        )

    def choose_export_folder(self):
        start_dir = self.export_dir.text() or "export"
        folder = QFileDialog.getExistingDirectory(
            self, self.strings.get("select_folder", ""), start_dir
        )
        if folder:
            self.export_dir.setText(folder)

    def get_export_dir(self) -> str:
        return self.export_dir.text().strip()

    def set_language(self, language: str):
        language = ensure_language(language)
        self.language = language
        strings = get_section(language, "export")
        self.strings = strings

        self.export_dir.setPlaceholderText(strings.get("directory_placeholder", ""))
        self.choose_btn.setText(strings.get("choose_folder", ""))
        self.export_btn.setText(strings.get("export_pdf", ""))
        self.language_box.setTitle(strings.get("language_label", ""))

        language_labels = strings.get("languages", self.available_languages)
        for code, button in self.language_buttons.items():
            button.blockSignals(True)
            button.setText(language_labels.get(code, self.available_languages.get(code, code)))
            button.setChecked(code == language)
            button.blockSignals(False)

    def _on_language_toggle(self, selected_language: str, checked: bool):
        if not checked:
            return
        selected_language = ensure_language(selected_language)
        if selected_language != self.language:
            self.set_language(selected_language)
            self.languageChanged.emit(selected_language)

    def _emit_error(self, title: str, message: str, level: str = "error"):
        if self.error_notifier:
            self.error_notifier.emit_error(title, message, level)
    
