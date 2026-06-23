"""Banner when scenario text needs apply or has parse errors."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

_MESSAGES = {
    "parse_error": "В тексте сценария есть ошибки — тест пойдёт по последней рабочей версии",
    "unapplied": "Текст сценария изменён — примените к шагам (Ctrl+Shift+S) перед запуском",
}


class DirtyBanner(QWidget):
    apply_clicked = Signal()
    discard_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "dirty-banner")
        self.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        icon = QLabel("⚠")
        icon.setProperty("role", "banner-warning-icon")
        layout.addWidget(icon)

        self._text = QLabel(_MESSAGES["parse_error"])
        self._text.setWordWrap(True)
        layout.addWidget(self._text, stretch=1)

        self._apply_btn = QPushButton("Применить")
        self._apply_btn.setToolTip("Обновить шаги из текста (Ctrl+Shift+S)")
        self._apply_btn.clicked.connect(self.apply_clicked.emit)
        layout.addWidget(self._apply_btn)

        discard_btn = QPushButton("Сбросить")
        discard_btn.setToolTip("Вернуть последнюю рабочую версию сценария")
        discard_btn.clicked.connect(self.discard_clicked.emit)
        layout.addWidget(discard_btn)

        self._mode = "parse_error"

    def set_banner(self, *, visible: bool, mode: str = "parse_error") -> None:
        self._mode = mode if mode in _MESSAGES else "parse_error"
        self._text.setText(_MESSAGES[self._mode])
        self._apply_btn.setVisible(self._mode == "unapplied")
        self.setVisible(visible)

    def set_visible(self, visible: bool) -> None:
        self.set_banner(visible=visible, mode=self._mode)
