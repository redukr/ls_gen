from PySide6.QtWidgets import QMainWindow, QTabWidget

from ui.ai_tab import AiGeneratorTab
from ui.data_tab import DataTab
from ui.export_tab import ExportTab
from ui.render_tab import RenderTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("LS_gen — AI Generator + Card Renderer")
        self.setMinimumSize(400, 300)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.rendered_cards: list[str] = []

        self.ai_tab = AiGeneratorTab()
        self.export_tab = ExportTab(self.get_rendered_cards)
        self.render_tab = RenderTab(
            get_generated_images=self.ai_tab.get_generated_images,
            get_export_dir=self.export_tab.get_export_dir,
        )
        self.data_tab = DataTab()

        self.render_tab.cardsRendered.connect(self._update_rendered_cards)

        self.tabs.addTab(self.ai_tab, "AI Generator")
        self.tabs.addTab(self.render_tab, "Card Renderer")
        self.tabs.addTab(self.export_tab, "Export")
        self.tabs.addTab(self.data_tab, "Data Editor")

    def _update_rendered_cards(self, cards: list[str]):
        self.rendered_cards = cards

    def get_rendered_cards(self) -> list[str]:
        return self.rendered_cards
