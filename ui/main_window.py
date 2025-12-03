from PySide6.QtWidgets import QMainWindow, QTabWidget

from ui.ai_tab import AiGeneratorTab
from ui.data_tab import DataTab
from ui.export_tab import ExportTab
from ui.render_tab import RenderTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.language = "en"
        self.strings = {
            "en": {
                "title": "LS_gen — AI Generator + Card Renderer",
                "ai": "AI Generator",
                "render": "Card Renderer",
                "export": "Export",
                "data": "Data Editor",
            },
            "uk": {
                "title": "LS_gen — Генератор ШІ + Рендер карток",
                "ai": "Генератор ШІ",
                "render": "Рендер карток",
                "export": "Експорт",
                "data": "Редактор даних",
            },
        }

        self.setMinimumSize(400, 300)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.rendered_cards: list[str] = []

        self.ai_tab = AiGeneratorTab()
        self.export_tab = ExportTab(self.get_rendered_cards)
        self.export_tab.languageChanged.connect(self.on_language_changed)
        self.render_tab = RenderTab(
            get_generated_images=self.ai_tab.get_generated_images,
            get_export_dir=self.export_tab.get_export_dir,
        )
        self.data_tab = DataTab()

        self.render_tab.cardsRendered.connect(self._update_rendered_cards)

        self.tabs.addTab(self.ai_tab, "")
        self.tabs.addTab(self.render_tab, "")
        self.tabs.addTab(self.export_tab, "")
        self.tabs.addTab(self.data_tab, "")

        self.set_language(self.language)

    def _update_rendered_cards(self, cards: list[str]):
        self.rendered_cards = cards

    def get_rendered_cards(self) -> list[str]:
        return self.rendered_cards

    def set_language(self, language: str):
        if language not in self.strings:
            return
        self.language = language
        texts = self.strings[language]
        self.setWindowTitle(texts["title"])
        self.tabs.setTabText(0, texts["ai"])
        self.tabs.setTabText(1, texts["render"])
        self.tabs.setTabText(2, texts["export"])
        self.tabs.setTabText(3, texts["data"])
        self.ai_tab.set_language(language)
        self.render_tab.set_language(language)
        self.export_tab.set_language(language)
        self.data_tab.set_language(language)

    def on_language_changed(self, language: str):
        self.set_language(language)
