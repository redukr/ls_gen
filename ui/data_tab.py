import csv
import json
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from renderer.widgets.translator import OfflineTranslator


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
        self.headers: list[str] = []
        self.current_path: str | None = None
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
        headers: list[str] = []
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


class DataTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.data_editor = DataEditorWidget()
        layout.addWidget(self.data_editor)
        self.setLayout(layout)
