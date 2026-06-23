"""List + action footer pattern for settings-style manager dialogs."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QHBoxLayout, QListWidget, QPushButton

from app.qt.dialog_buttons import BTN_CLOSE
from app.qt.widgets.base_dialog import BaseAppDialog, dialog_action_button


class ListManagerDialog(BaseAppDialog):
    def __init__(
        self,
        parent=None,
        *,
        title: str,
        hint: str,
        min_size: tuple[int, int] = (560, 380),
    ) -> None:
        super().__init__(parent, title=title, min_size=min_size)
        self.add_hint(hint)

        self._list = QListWidget()
        self._list.setProperty("role", "settings-list")
        self.content_layout.addWidget(self._list, stretch=1)

        self.add_footer_line()
        self._footer_row = QHBoxLayout()
        self._footer_row.setSpacing(8)
        self._footer_row.setContentsMargins(0, 4, 0, 0)
        self.content_layout.addLayout(self._footer_row)

    @property
    def list_widget(self) -> QListWidget:
        return self._list

    def add_action(
        self,
        text: str,
        handler: Callable[[], None],
        *,
        primary: bool = False,
    ) -> QPushButton:
        btn = dialog_action_button(text, primary=primary)
        btn.clicked.connect(handler)
        self._footer_row.addWidget(btn)
        return btn

    def add_close(self, text: str = BTN_CLOSE) -> QPushButton:
        self._footer_row.addStretch()
        btn = dialog_action_button(text)
        btn.clicked.connect(self.accept)
        self._footer_row.addWidget(btn)
        return btn
