"""Shared layout and styling for Scenaria modal dialogs."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.qt.dialog_buttons import BTN_CLOSE, close_button_box, ok_cancel_button_box
from app.qt.labels import dialog_hint_label

DIALOG_MARGIN = 16
DIALOG_SPACING = 12


def dialog_action_button(
    text: str,
    *,
    primary: bool = False,
    default: bool = False,
) -> QPushButton:
    btn = QPushButton(text)
    btn.setProperty("dialog-action", True)
    if primary:
        btn.setProperty("primary", True)
    if default:
        btn.setDefault(True)
    return btn


def style_dialog_button_box(box: QDialogButtonBox) -> None:
    for btn in box.buttons():
        btn.setProperty("dialog-action", True)


class BaseAppDialog(QDialog):
    """Standard Scenaria dialog shell: margins, role, footer helpers."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        title: str,
        min_width: int = 0,
        min_height: int = 0,
        min_size: tuple[int, int] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setProperty("role", "app-dialog")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        if min_size is not None:
            self.setMinimumSize(*min_size)
        else:
            if min_width:
                self.setMinimumWidth(min_width)
            if min_height:
                self.setMinimumHeight(min_height)

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(DIALOG_MARGIN, DIALOG_MARGIN, DIALOG_MARGIN, DIALOG_MARGIN)
        self._root.setSpacing(DIALOG_SPACING)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._root

    def add_hint(self, text: str) -> QLabel:
        label = dialog_hint_label(text)
        self._root.addWidget(label)
        return label

    def add_footer_line(self) -> QFrame:
        line = QFrame()
        line.setProperty("role", "dialog-footer-line")
        line.setFrameShape(QFrame.Shape.HLine)
        self._root.addWidget(line)
        return line

    def add_button_row(self, *buttons: QPushButton) -> QHBoxLayout:
        self.add_footer_line()
        row = QHBoxLayout()
        row.setSpacing(8)
        row.setContentsMargins(0, 4, 0, 0)
        for index, btn in enumerate(buttons):
            if index == len(buttons) - 1 and len(buttons) > 1:
                row.addStretch()
            row.addWidget(btn)
        self._root.addLayout(row)
        return row

    def add_ok_cancel(self) -> QDialogButtonBox:
        self.add_footer_line()
        box = ok_cancel_button_box()
        style_dialog_button_box(box)
        self._root.addWidget(box)
        return box

    def add_close_box(self) -> QDialogButtonBox:
        self.add_footer_line()
        box = close_button_box()
        style_dialog_button_box(box)
        self._root.addWidget(box)
        return box

    def add_close_button(self, text: str = BTN_CLOSE) -> QPushButton:
        btn = dialog_action_button(text)
        btn.clicked.connect(self.accept)
        return btn

