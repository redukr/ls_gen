import os

from PySide6.QtWidgets import (
    QFileDialog,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from renderer.core.pdf_exporter import export_pdf_from_list


class ExportTab(QWidget):
    def __init__(self, get_rendered_cards, parent=None):
        super().__init__(parent)
        self.get_rendered_cards = get_rendered_cards

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

        self.setLayout(layout)

    def export_pdf_deck(self):
        rendered_cards = self.get_rendered_cards()
        if not rendered_cards:
            QMessageBox.warning(self, "Error", "Render a card first")
            return

        export_path = self.export_dir.text().strip() or "export"
        os.makedirs(export_path, exist_ok=True)

        out = os.path.join(export_path, "deck.pdf")
        export_pdf_from_list(rendered_cards, out)

        QMessageBox.information(self, "Done", f"PDF exported: {out}")

    def choose_export_folder(self):
        start_dir = self.export_dir.text() or "export"
        folder = QFileDialog.getExistingDirectory(self, "Select export folder", start_dir)
        if folder:
            self.export_dir.setText(folder)

    def get_export_dir(self) -> str:
        return self.export_dir.text().strip()
