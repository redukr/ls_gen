import os

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from renderer.core.pdf_exporter import export_pdf_from_list


class ExportTab(QWidget):
    languageChanged = Signal(str)

    def __init__(self, get_rendered_cards, parent=None):
        super().__init__(parent)
        self.get_rendered_cards = get_rendered_cards
        self.language = "en"

        self.strings = {
            "en": {
                "directory_placeholder": "Select export directory...",
                "choose_folder": "Choose folder",
                "export_pdf": "Export deck to PDF",
                "error_title": "Error",
                "render_first": "Render a card first",
                "done_title": "Done",
                "pdf_exported": "PDF exported: {path}",
                "select_folder": "Select export folder",
                "language_label": "Interface Language",
                "english": "English",
                "ukrainian": "Українська",
            },
            "uk": {
                "directory_placeholder": "Оберіть теку для експорту...",
                "choose_folder": "Вибрати теку",
                "export_pdf": "Експортувати колоду у PDF",
                "error_title": "Помилка",
                "render_first": "Спочатку відрендерте картку",
                "done_title": "Готово",
                "pdf_exported": "PDF збережено: {path}",
                "select_folder": "Виберіть теку для експорту",
                "language_label": "Мова інтерфейсу",
                "english": "English",
                "ukrainian": "Українська",
            },
        }

        layout = QVBoxLayout()

        self.export_dir = QLineEdit()
        self.export_dir.setPlaceholderText(self.strings[self.language]["directory_placeholder"])
        layout.addWidget(self.export_dir)

        self.choose_btn = QPushButton(self.strings[self.language]["choose_folder"])
        self.choose_btn.clicked.connect(self.choose_export_folder)
        layout.addWidget(self.choose_btn)

        self.export_btn = QPushButton(self.strings[self.language]["export_pdf"])
        self.export_btn.clicked.connect(self.export_pdf_deck)
        layout.addWidget(self.export_btn)

        self.language_box = QGroupBox(self.strings[self.language]["language_label"])
        language_layout = QHBoxLayout()
        self.language_en = QRadioButton(self.strings[self.language]["english"])
        self.language_uk = QRadioButton(self.strings[self.language]["ukrainian"])
        self.language_en.setChecked(True)
        self.language_en.toggled.connect(self._on_language_toggle)
        language_layout.addWidget(self.language_en)
        language_layout.addWidget(self.language_uk)
        self.language_box.setLayout(language_layout)
        layout.addWidget(self.language_box)

        self.setLayout(layout)

    def export_pdf_deck(self):
        rendered_cards = self.get_rendered_cards()
        if not rendered_cards:
            QMessageBox.warning(
                self,
                self.strings[self.language]["error_title"],
                self.strings[self.language]["render_first"],
            )
            return

        export_path = self.export_dir.text().strip() or "export"
        os.makedirs(export_path, exist_ok=True)

        out = os.path.join(export_path, "deck.pdf")
        export_pdf_from_list(rendered_cards, out)

        QMessageBox.information(
            self,
            self.strings[self.language]["done_title"],
            self.strings[self.language]["pdf_exported"].format(path=out),
        )

    def choose_export_folder(self):
        start_dir = self.export_dir.text() or "export"
        folder = QFileDialog.getExistingDirectory(
            self, self.strings[self.language]["select_folder"], start_dir
        )
        if folder:
            self.export_dir.setText(folder)

    def get_export_dir(self) -> str:
        return self.export_dir.text().strip()

    def set_language(self, language: str):
        if language not in self.strings:
            return
        self.language = language
        strings = self.strings[language]
        self.export_dir.setPlaceholderText(strings["directory_placeholder"])
        self.choose_btn.setText(strings["choose_folder"])
        self.export_btn.setText(strings["export_pdf"])
        # Update group box and buttons without retriggering signal
        self.language_en.blockSignals(True)
        self.language_uk.blockSignals(True)
        self.language_en.setText(strings["english"])
        self.language_uk.setText(strings["ukrainian"])
        if language == "en":
            self.language_en.setChecked(True)
        else:
            self.language_uk.setChecked(True)
        self.language_en.blockSignals(False)
        self.language_uk.blockSignals(False)
        self.language_box.setTitle(strings["language_label"])

    def _on_language_toggle(self, checked: bool):
        if not checked:
            return
        selected = "en" if self.language_en.isChecked() else "uk"
        if selected != self.language:
            self.set_language(selected)
            self.languageChanged.emit(selected)
