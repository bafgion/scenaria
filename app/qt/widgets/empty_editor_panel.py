"""Empty workspace hints when no editor tabs are open (VS Code style)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from app.qt.theme import COLOR_MUTED, COLOR_PRIMARY


class EmptyEditorPanel(QWidget):
    show_start = Signal()
    open_project = Signal()
    create_feature = Signal()
    open_feature = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "empty-editor")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.addStretch(1)

        card = QWidget(self)
        card.setProperty("role", "empty-editor-card")
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(6)
        layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)

        title = QLabel("Нет открытых сценариев")
        title.setStyleSheet("font-size: 14pt; font-weight: 300;")
        layout.addWidget(title)

        hint = QLabel("Выберите действие ниже или откройте страницу «Старт»")
        hint.setProperty("muted", True)
        hint.setWordWrap(True)
        hint.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
        hint.setMinimumWidth(280)
        hint.setMaximumWidth(360)
        hint.setStyleSheet(f"color: {COLOR_MUTED}; margin-bottom: 12px;")
        layout.addWidget(hint)

        for text, shortcut, handler in (
            ("Страница «Старт»", "", self.show_start.emit),
            ("Новый сценарий", "Ctrl+N", self.create_feature.emit),
            ("Открыть файл…", "Ctrl+O", self.open_feature.emit),
            ("Открыть папку…", "", self.open_project.emit),
        ):
            self._add_action_row(layout, text, shortcut, handler)

        layout.addSpacing(12)
        tips = QLabel(
            "Совет:\n"
            "1. Откройте сайт\n"
            "2. Запишите действия\n"
            "3. Запустите сценарий"
        )
        tips.setProperty("role", "empty-editor-tips")
        tips.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        tips.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        layout.addWidget(tips)

        outer.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(2)

    def _add_action_row(self, layout: QVBoxLayout, text: str, shortcut: str, handler) -> None:
        row = QHBoxLayout()
        row.setContentsMargins(0, 2, 0, 2)
        row.setSpacing(12)

        link = QLabel(f'<a href="#">{text}</a>')
        link.setTextFormat(Qt.TextFormat.RichText)
        link.setOpenExternalLinks(False)
        link.setStyleSheet(f"QLabel a {{ color: {COLOR_PRIMARY}; text-decoration: none; font-size: 9pt; }}")
        link.linkActivated.connect(lambda _href, fn=handler: fn())
        row.addWidget(link, stretch=1)

        if shortcut:
            keys = QLabel(shortcut)
            keys.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            keys.setStyleSheet(f"color: {COLOR_MUTED}; font-size: 8pt;")
            row.addWidget(keys)

        layout.addLayout(row)
