from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMainWindow, QTabWidget

from ui.ai_tab import AiGeneratorTab
from ui.data_tab import DataTab
from ui.export_tab import ExportTab
from ui.error_window import ErrorLogWidget
from ui.render_tab import RenderTab
from ui.locales import ensure_language, get_section


class ErrorNotifier(QObject):
    errorOccurred = Signal(str, str, str)

    def emit_error(self, title: str, message: str, level: str = "error"):
        self.errorOccurred.emit(title, message, level)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.language = ensure_language("en")

        self.error_notifier = ErrorNotifier()

        self.setMinimumSize(400, 300)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.rendered_cards: list[str] = []

        self.ai_tab = AiGeneratorTab(error_notifier=self.error_notifier)
        self.export_tab = ExportTab(self.get_rendered_cards, error_notifier=self.error_notifier)
        self.export_tab.languageChanged.connect(self.on_language_changed)
        self.render_tab = RenderTab(
            get_generated_images=self.ai_tab.get_generated_images,
            get_export_dir=self.export_tab.get_export_dir,
            error_notifier=self.error_notifier,
        )
        self.data_tab = DataTab(error_notifier=self.error_notifier)
        self.error_log_tab = ErrorLogWidget()
        self.error_notifier.errorOccurred.connect(self.error_log_tab.add_entry)

        self.render_tab.cardsRendered.connect(self._update_rendered_cards)

        self.tabs.addTab(self.ai_tab, "")
        self.tabs.addTab(self.render_tab, "")
        self.tabs.addTab(self.export_tab, "")
        self.tabs.addTab(self.data_tab, "")
        self.tabs.addTab(self.error_log_tab, "")

        self.set_language(self.language)

    def _update_rendered_cards(self, cards: list[str]):
        self.rendered_cards = cards

    def get_rendered_cards(self) -> list[str]:
        return self.rendered_cards

    def set_language(self, language: str):
        language = ensure_language(language)
        self.language = language
        app_strings = get_section(language, "app")
        tabs_strings = get_section(language, "tabs")
        error_strings = get_section(language, "error_log")

        title = app_strings.get("window_title")
        if not title:
            name = app_strings.get("name", "LS_gen")
            version = app_strings.get("version", "")
            title = f"{name} {version}".strip()

        self.setWindowTitle(title)
        self.tabs.setTabText(0, tabs_strings.get("ai_generator", "AI Generator"))
        self.tabs.setTabText(1, tabs_strings.get("render", "Card Renderer"))
        self.tabs.setTabText(2, tabs_strings.get("export", "Export"))
        self.tabs.setTabText(3, tabs_strings.get("data_editor", "Data Editor"))
        self.tabs.setTabText(4, error_strings.get("tab_title", "Errors"))
        if self.ai_tab.preview_window:
            preview_index = self.tabs.indexOf(self.ai_tab.preview_window)
            if preview_index != -1:
                self.tabs.setTabText(
                    preview_index, tabs_strings.get("preview_gen", "Preview Gen")
                )
                self.ai_tab.preview_window.set_language(language)
        self.ai_tab.set_language(language)
        self.render_tab.set_language(language)
        self.export_tab.set_language(language)
        self.data_tab.set_language(language)
        self.error_log_tab.set_language(language)

    def on_language_changed(self, language: str):
        self.set_language(language)
