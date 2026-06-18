"""Bottom output panel (VS Code terminal style)."""

from __future__ import annotations

from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from app.qt.widgets.error_panel import ErrorPanel
from app.qt.widgets.log_panel import LogPanel
from app.qt.widgets.results_panel import ResultsPanel


class BottomPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "panel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setProperty("role", "bottom-panel-tabs")
        self.tabs.setDocumentMode(True)
        self.tabs.tabBar().setProperty("role", "panel-tabs")
        self.tabs.tabBar().setDrawBase(False)
        self.log_panel = LogPanel(self.tabs)
        self.results_panel = ResultsPanel(self.tabs)
        self.error_panel = ErrorPanel(self.tabs)
        self.tabs.addTab(self.log_panel, "Журнал")
        self.tabs.addTab(self.results_panel, "Результаты")
        self.tabs.addTab(self.error_panel, "Ошибка")
        layout.addWidget(self.tabs)

    def show_page(self, key: str) -> None:
        mapping = {
            "log": self.log_panel,
            "results": self.results_panel,
            "error": self.error_panel,
        }
        widget = mapping.get(key)
        if widget is not None:
            self.tabs.setCurrentWidget(widget)
