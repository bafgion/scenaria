"""Recording and selector strategy preferences — opens unified settings."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QWidget

from app.qt.widgets.settings_dialog import open_settings_dialog


def open_recording_settings_dialog(parent: QWidget | None) -> bool:
    result = open_settings_dialog(parent, initial_tab="recording")
    return result.saved
