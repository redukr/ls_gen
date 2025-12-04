from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.locales import ensure_language, get_section


class ErrorLogWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.language = ensure_language("en")
        self.strings: dict = {}

        layout = QVBoxLayout()

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["", "", "", ""])
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self.update_copy_button_state)
        layout.addWidget(self.table)

        controls = QHBoxLayout()
        self.copy_button = QPushButton()
        self.copy_button.clicked.connect(self.copy_selected)
        controls.addWidget(self.copy_button)
        self.clear_button = QPushButton()
        self.clear_button.clicked.connect(self.clear_entries)
        controls.addWidget(self.clear_button)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.setLayout(layout)
        self.set_language(self.language)

    def set_language(self, language: str):
        language = ensure_language(language)
        self.language = language
        self.strings = get_section(language, "error_log")

        headers = [
            self.strings.get("timestamp", ""),
            self.strings.get("level", ""),
            self.strings.get("title", ""),
            self.strings.get("details", ""),
        ]
        for idx, text in enumerate(headers):
            self.table.horizontalHeaderItem(idx).setText(text)

        self.copy_button.setText(self.strings.get("copy", ""))
        self.clear_button.setText(self.strings.get("clear", ""))

        self.update_copy_button_state()

    def add_entry(self, title: str, message: str, level: str = "error"):
        row = self.table.rowCount()
        self.table.insertRow(row)

        timestamp_item = QTableWidgetItem(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        level_item = QTableWidgetItem(level)
        title_item = QTableWidgetItem(title)
        message_item = QTableWidgetItem(message)

        for item in (timestamp_item, level_item, title_item, message_item):
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)

        self.table.setItem(row, 0, timestamp_item)
        self.table.setItem(row, 1, level_item)
        self.table.setItem(row, 2, title_item)
        self.table.setItem(row, 3, message_item)

        self.table.resizeColumnsToContents()

    def clear_entries(self):
        self.table.setRowCount(0)
        self.update_copy_button_state()

    def copy_selected(self):
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        if not rows:
            return

        clipboard = QGuiApplication.clipboard()
        entries: list[str] = []
        for row in rows:
            timestamp = self.table.item(row, 0)
            level = self.table.item(row, 1)
            title = self.table.item(row, 2)
            message = self.table.item(row, 3)

            formatted = " | ".join(
                filter(
                    None,
                    (
                        timestamp.text() if timestamp else "",
                        level.text() if level else "",
                        title.text() if title else "",
                        message.text() if message else "",
                    ),
                )
            )
            entries.append(formatted)

        clipboard.setText("\n".join(entries))

    def update_copy_button_state(self):
        has_selection = bool(self.table.selectedIndexes())
        self.copy_button.setEnabled(has_selection)


class ErrorLogDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.widget = ErrorLogWidget()
        layout.addWidget(self.widget)
        self.setLayout(layout)

    def set_language(self, language: str):
        self.widget.set_language(language)
        title = self.widget.strings.get("window_title")
        if title:
            self.setWindowTitle(title)

    def add_entry(self, title: str, message: str, level: str = "error"):
        self.widget.add_entry(title, message, level)
