import json
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

    def __init__(
        self,
        get_rendered_cards,
        get_ai_settings=None,
        apply_ai_settings=None,
        parent=None,
        error_notifier=None,
    ):
        super().__init__(parent)
        self.get_rendered_cards = get_rendered_cards
        self.get_ai_settings = get_ai_settings
        self.apply_ai_settings = apply_ai_settings
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

        self.settings_dir = QLineEdit()
        self.settings_dir.setPlaceholderText("")
        layout.addWidget(self.settings_dir)

        self.choose_settings_btn = QPushButton()
        self.choose_settings_btn.clicked.connect(self.choose_settings_folder)
        layout.addWidget(self.choose_settings_btn)

        settings_row = QHBoxLayout()
        self.load_settings_btn = QPushButton()
        self.load_settings_btn.clicked.connect(self.load_settings)
        settings_row.addWidget(self.load_settings_btn)

        self.save_settings_btn = QPushButton()
        self.save_settings_btn.clicked.connect(self.save_settings)
        settings_row.addWidget(self.save_settings_btn)

        layout.addLayout(settings_row)

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

    def _gather_settings(self) -> dict:
        settings = {
            "language": self.language,
            "export_dir": self.get_export_dir(),
            "settings_dir": self.get_settings_dir(),
        }
        if self.get_ai_settings:
            settings["ai_generator"] = self.get_ai_settings()
        return settings

    def get_settings_dir(self) -> str:
        return self.settings_dir.text().strip()

    def save_settings(self):
        start_dir = self.get_settings_dir() or self.get_export_dir() or "config"
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.strings.get("save_settings", ""),
            start_dir,
            "JSON (*.json)",
        )
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        self.settings_dir.setText(os.path.dirname(path))
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._gather_settings(), f, ensure_ascii=False, indent=2)
        except Exception as exc:
            self._emit_error(
                self.strings.get("error_title", ""),
                format_message(self.strings, "save_failed", error=exc),
            )
            return
        self._emit_error(
            self.strings.get("done_title", ""),
            format_message(self.strings, "settings_saved", path=path),
            level="info",
        )

    def load_settings(self):
        start_dir = self.get_settings_dir() or self.get_export_dir() or "config"
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.strings.get("load_settings", ""),
            start_dir,
            "JSON (*.json)",
        )
        if not path:
            return
        self.settings_dir.setText(os.path.dirname(path))
        try:
            with open(path, encoding="utf-8") as f:
                loaded = json.load(f)
            if not isinstance(loaded, dict):
                raise ValueError("Settings file must contain a JSON object")
        except Exception as exc:
            self._emit_error(
                self.strings.get("error_title", ""),
                format_message(self.strings, "load_failed", error=exc),
            )
            return

        self.export_dir.setText(loaded.get("export_dir", ""))
        if "settings_dir" in loaded:
            self.settings_dir.setText(str(loaded.get("settings_dir") or ""))
        loaded_language = loaded.get("language")
        if loaded_language:
            loaded_language = ensure_language(loaded_language)
            if loaded_language != self.language:
                self.set_language(loaded_language)
                self.languageChanged.emit(loaded_language)
        ai_settings = loaded.get("ai_generator")
        if ai_settings and self.apply_ai_settings:
            self.apply_ai_settings(ai_settings)
        self._emit_error(
            self.strings.get("done_title", ""),
            format_message(self.strings, "settings_loaded", path=path),
            level="info",
        )

    def set_language(self, language: str):
        language = ensure_language(language)
        self.language = language
        strings = get_section(language, "export")
        self.strings = strings

        self.export_dir.setPlaceholderText(strings.get("directory_placeholder", ""))
        self.settings_dir.setPlaceholderText(strings.get("settings_directory_placeholder", ""))
        self.choose_btn.setText(strings.get("choose_folder", ""))
        self.choose_settings_btn.setText(strings.get("choose_settings_folder", ""))
        self.load_settings_btn.setText(strings.get("load_settings", ""))
        self.save_settings_btn.setText(strings.get("save_settings", ""))
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

    def choose_settings_folder(self):
        start_dir = self.get_settings_dir() or self.get_export_dir() or "config"
        folder = QFileDialog.getExistingDirectory(
            self, self.strings.get("choose_settings_folder", ""), start_dir
        )
        if folder:
            self.settings_dir.setText(folder)
    
