"""Banner for unapplied Gherkin edits."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from app.qt.theme import COLOR_WARNING


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
        icon.setStyleSheet(f"color: {COLOR_WARNING};")
        layout.addWidget(icon)

        text = QLabel("Изменения не применены — тест пойдёт по старой версии сценария")
        text.setWordWrap(True)
        layout.addWidget(text, stretch=1)

        apply_btn = QPushButton("Применить")
        apply_btn.setProperty("primary", True)
        apply_btn.clicked.connect(self.apply_clicked.emit)
        layout.addWidget(apply_btn)

        discard_btn = QPushButton("Сбросить")
        discard_btn.clicked.connect(self.discard_clicked.emit)
        layout.addWidget(discard_btn)

    def set_visible(self, visible: bool) -> None:
        self.setVisible(visible)
