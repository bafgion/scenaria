"""Log output."""

from __future__ import annotations

from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget

from app.qt.fonts import editor_font
from app.qt.theme import COLOR_ERROR, COLOR_MUTED, COLOR_SUCCESS


class LogPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setPlaceholderText("Журнал…")
        self.editor.setProperty("role", "mono-panel")
        self.editor.setFont(editor_font())
        layout.addWidget(self.editor)

        self._fmt_error = QTextCharFormat()
        self._fmt_error.setForeground(QColor(COLOR_ERROR))
        self._fmt_success = QTextCharFormat()
        self._fmt_success.setForeground(QColor(COLOR_SUCCESS))
        self._fmt_info = QTextCharFormat()
        self._fmt_info.setForeground(QColor(COLOR_MUTED))

    def append(self, message: str, tag: str = "info") -> None:
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if tag == "error":
            cursor.insertText(message + "\n", self._fmt_error)
        elif tag == "success":
            cursor.insertText(message + "\n", self._fmt_success)
        else:
            cursor.insertText(message + "\n", self._fmt_info)
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()
