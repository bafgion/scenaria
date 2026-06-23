"""Visible quick-fix bar for Gherkin parse errors."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from app.gherkin_quick_fixes import QuickFix
from app.qt.labels import caption_label, error_label


class GherkinErrorBar(QWidget):
    fix_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "gherkin-error-bar")
        self.setVisible(False)

        root = QHBoxLayout(self)
        root.setContentsMargins(6, 4, 6, 4)
        root.setSpacing(8)

        self._message = error_label(word_wrap=True)
        root.addWidget(self._message, stretch=1)

        self._buttons_host = QWidget()
        self._buttons = QHBoxLayout(self._buttons_host)
        self._buttons.setContentsMargins(0, 0, 0, 0)
        self._buttons.setSpacing(6)
        root.addWidget(self._buttons_host)

        hint = caption_label("Правый клик по строке → «Исправить»")
        root.addWidget(hint)

    def show_error(self, message: str, fixes: list[tuple[QuickFix, str]], *, source_text: str) -> None:
        self._message.setText(message)
        while item := self._buttons.takeAt(0):
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for quick_fix, new_text in fixes:
            if quick_fix.label == "Открыть палитру шагов (Ctrl+Shift+Space)":
                continue
            if new_text == source_text:
                continue
            button = QPushButton(quick_fix.label)
            button.setToolTip(quick_fix.description)
            button.setProperty("toolbar", True)
            button.clicked.connect(lambda _checked=False, payload=new_text: self.fix_requested.emit(payload))
            self._buttons.addWidget(button)

        self.setVisible(True)

    def hide_error(self) -> None:
        self.setVisible(False)
