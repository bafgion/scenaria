"""Visible start URL bar."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QToolButton, QWidget

from app.qt import icons
from app.qt.theme import COLOR_MUTED, COLOR_SUCCESS


class UrlBar(QWidget):
    edit_requested = Signal()
    fetch_from_tab_requested = Signal()
    url_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "url-bar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(4)

        globe = QLabel("🌐")
        globe.setToolTip("Стартовый URL")
        layout.addWidget(globe)

        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("https://site.com")
        self._url_edit.returnPressed.connect(self._commit_url)
        layout.addWidget(self._url_edit, stretch=1)

        edit_btn = QToolButton()
        edit_btn.setIcon(icons.icon("url"))
        edit_btn.setIconSize(icons.icon_size())
        edit_btn.setToolTip("Изменить URL…")
        edit_btn.setProperty("compact-icon", True)
        edit_btn.clicked.connect(self.edit_requested.emit)
        layout.addWidget(edit_btn)

        tab_btn = QToolButton()
        tab_btn.setText("из вкладки")
        tab_btn.setToolTip("Взять URL из активной вкладки браузера")
        tab_btn.setProperty("toolbar", True)
        tab_btn.clicked.connect(self.fetch_from_tab_requested.emit)
        layout.addWidget(tab_btn)

        self._status = QLabel("")
        self._status.setStyleSheet(f"color: {COLOR_MUTED}; font-size: 8pt;")
        layout.addWidget(self._status)

    def set_url(self, url: str) -> None:
        blocked = self._url_edit.blockSignals(True)
        self._url_edit.setText(url)
        self._url_edit.blockSignals(blocked)

    def _commit_url(self) -> None:
        self.url_changed.emit(self._url_edit.text().strip())

    def set_browser_open(self, open_: bool) -> None:
        if open_:
            self._status.setText("браузер открыт")
            self._status.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: 8pt;")
        else:
            self._status.setText("браузер закрыт")
            self._status.setStyleSheet(f"color: {COLOR_MUTED}; font-size: 8pt;")
