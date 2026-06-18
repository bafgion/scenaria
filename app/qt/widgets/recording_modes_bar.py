"""Recording mode toggles visible during browser/recording."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QWidget

from app.qt.theme import COLOR_MUTED


class RecordingModesBar(QWidget):
    filter_toggled = Signal(bool)
    nav_only_toggled = Signal(bool)
    headless_toggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "recording-modes")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(12)

        label = QLabel("Запись:")
        label.setStyleSheet(f"color: {COLOR_MUTED}; font-size: 8pt;")
        layout.addWidget(label)

        self._filter = QCheckBox("Только важные")
        self._filter.setToolTip("Клики по cookie-баннерам и важным элементам")
        self._filter.toggled.connect(self._on_filter)
        layout.addWidget(self._filter)

        self._nav_only = QCheckBox("Только ссылки")
        self._nav_only.setToolTip("Записывать только переходы по ссылкам")
        self._nav_only.toggled.connect(self._on_nav_only)
        layout.addWidget(self._nav_only)

        self._headless = QCheckBox("Headless")
        self._headless.setToolTip("Запуск теста без видимого окна браузера")
        self._headless.toggled.connect(self.headless_toggled.emit)
        layout.addWidget(self._headless)

        layout.addStretch()
        self.hide()

    def _on_filter(self, checked: bool) -> None:
        if checked:
            self._nav_only.blockSignals(True)
            self._nav_only.setChecked(False)
            self._nav_only.blockSignals(False)
        self.filter_toggled.emit(checked)

    def _on_nav_only(self, checked: bool) -> None:
        if checked:
            self._filter.blockSignals(True)
            self._filter.setChecked(False)
            self._filter.blockSignals(False)
        self.nav_only_toggled.emit(checked)

    def sync(
        self,
        *,
        visible: bool,
        filter_recording: bool,
        nav_only_recording: bool,
        headless: bool,
    ) -> None:
        self.setVisible(visible)
        for box, value in (
            (self._filter, filter_recording),
            (self._nav_only, nav_only_recording),
            (self._headless, headless),
        ):
            box.blockSignals(True)
            box.setChecked(value)
            box.blockSignals(False)
