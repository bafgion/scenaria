"""VS Code-style splitter: wide hit area, thin center line."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QSplitter, QSplitterHandle

from app.qt.theme import (
    COLOR_DIVIDER,
    COLOR_EDITOR,
    COLOR_PANEL,
    COLOR_SIDEBAR,
    COLOR_WORKSPACE,
    COLOR_ZONE_LINE,
)

HIT_SIZE = 9
LINE_SIZE = 1


class ThinSplitterHandle(QSplitterHandle):
    def __init__(self, orientation: Qt.Orientation, parent: QSplitter | None = None) -> None:
        super().__init__(orientation, parent)
        if orientation == Qt.Orientation.Horizontal:
            self.setCursor(Qt.CursorShape.SplitHCursor)
        else:
            self.setCursor(Qt.CursorShape.SplitVCursor)

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        role = str(self.splitter().property("role") or "")
        if self.orientation() == Qt.Orientation.Horizontal and role == "side-splitter":
            # Blend hit area into sidebar/editor colors so no visible "gap" appears.
            half = self.width() // 2
            painter.fillRect(0, 0, half, self.height(), QColor(COLOR_SIDEBAR))
            painter.fillRect(half, 0, self.width() - half, self.height(), QColor(COLOR_WORKSPACE))
        elif self.orientation() == Qt.Orientation.Vertical and role == "main-splitter":
            half = self.height() // 2
            painter.fillRect(0, 0, self.width(), half, QColor(COLOR_WORKSPACE))
            painter.fillRect(0, half, self.width(), self.height() - half, QColor(COLOR_PANEL))
        elif self.orientation() == Qt.Orientation.Vertical and role == "editor-splitter":
            half = self.height() // 2
            painter.fillRect(0, 0, self.width(), half, QColor(COLOR_EDITOR))
            painter.fillRect(0, half, self.width(), self.height() - half, QColor(COLOR_SIDEBAR))
        color = QColor(COLOR_ZONE_LINE if self.underMouse() else COLOR_DIVIDER)
        if self.orientation() == Qt.Orientation.Horizontal:
            x = (self.width() - LINE_SIZE) // 2
            painter.fillRect(x, 0, LINE_SIZE, self.height(), color)
        else:
            y = (self.height() - LINE_SIZE) // 2
            painter.fillRect(0, y, self.width(), LINE_SIZE, color)


class IdeSplitter(QSplitter):
    def __init__(self, orientation: Qt.Orientation, parent=None) -> None:
        super().__init__(orientation, parent)
        self.setHandleWidth(HIT_SIZE)
        self.setOpaqueResize(True)

    def createHandle(self) -> QSplitterHandle:  # noqa: N802
        return ThinSplitterHandle(self.orientation(), self)

    def sizeHint(self) -> QSize:  # noqa: N802
        return super().sizeHint()
