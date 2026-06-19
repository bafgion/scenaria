"""Narrow activity bar (VS Code style)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QToolButton, QVBoxLayout, QWidget

from app.qt import icons


class ActivityBar(QWidget):
    explorer_toggled = Signal(bool)
    panel_toggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "activity")
        self.setFixedWidth(40)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(0)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        self.explorer_btn = self._make_button(
            icons.explorer_icon(active=True),
            "Сценарии",
            checked=True,
        )
        self._group.addButton(self.explorer_btn)
        layout.addWidget(self.explorer_btn)

        self.panel_btn = self._make_button(icons.panel_icon(), "Панель вывода")
        layout.addWidget(self.panel_btn)

        layout.addStretch()

        self.explorer_btn.toggled.connect(self._update_explorer_icon)
        self.explorer_btn.toggled.connect(self.explorer_toggled.emit)
        self.panel_btn.toggled.connect(self._on_panel_toggled)

    def _make_button(self, qicon, tooltip: str, *, checked: bool = False) -> QToolButton:
        btn = QToolButton(self)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setIcon(qicon)
        btn.setIconSize(icons.icon_size(icons.SIZE_MD))
        btn.setToolTip(tooltip)
        btn.setProperty("activity", True)
        btn.setAutoRaise(True)
        return btn

    def _update_explorer_icon(self, checked: bool) -> None:
        self.explorer_btn.setIcon(icons.explorer_icon(active=checked))

    def _on_panel_toggled(self, checked: bool) -> None:
        self.panel_btn.setIcon(icons.panel_icon(active=checked))
        self.panel_toggled.emit(checked)

    def set_panel_checked(self, checked: bool) -> None:
        if self.panel_btn.isChecked() == checked:
            self.panel_btn.setIcon(icons.panel_icon(active=checked))
            return
        blocked = self.panel_btn.blockSignals(True)
        self.panel_btn.setChecked(checked)
        self.panel_btn.blockSignals(blocked)
        self.panel_btn.setIcon(icons.panel_icon(active=checked))

    def is_panel_checked(self) -> bool:
        return self.panel_btn.isChecked()
