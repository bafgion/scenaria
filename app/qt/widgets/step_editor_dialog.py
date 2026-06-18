"""Dialog for editing a single scenario step."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QWidget,
)

from app.step_display import ACTION_ICONS


class StepEditorDialog(QDialog):
    def __init__(self, parent: QWidget | None, step: dict[str, Any], *, index: int) -> None:
        super().__init__(parent)
        action = str(step.get("action", ""))
        icon = ACTION_ICONS.get(action, "•")
        self.setWindowTitle(f"Шаг {index + 1}")
        self._action = action
        self._fields: dict[str, QLineEdit] = {}

        layout = QFormLayout(self)
        layout.addRow(QLabel(f"{icon} {action}"))

        field_specs = _fields_for_action(action)
        for key, label in field_specs:
            edit = QLineEdit(str(step.get(key, "") or ""))
            if key == "selector":
                edit.setPlaceholderText("CSS-селектор или :has-text(...)")
            layout.addRow(label, edit)
            self._fields[key] = edit

        if not field_specs:
            layout.addRow(QLabel("Этот шаг не редактируется из диалога."))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        if not field_specs:
            buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        layout.addRow(buttons)

    def edited_step(self, original: dict[str, Any]) -> dict[str, Any] | None:
        if self.result() != QDialog.DialogCode.Accepted:
            return None
        step = dict(original)
        for key, edit in self._fields.items():
            value = edit.text().strip()
            if key in {"selector"} and not value and self._action not in {"press"}:
                return None
            if value:
                step[key] = value
            else:
                step.pop(key, None)
        return step


def _fields_for_action(action: str) -> list[tuple[str, str]]:
    specs: dict[str, list[tuple[str, str]]] = {
        "goto": [("url", "URL")],
        "click": [("selector", "Селектор")],
        "hover": [("selector", "Селектор")],
        "double_click": [("selector", "Селектор")],
        "fill": [("selector", "Селектор"), ("value", "Значение")],
        "clear": [("selector", "Селектор")],
        "select": [("selector", "Селектор"), ("value", "Значение")],
        "check": [("selector", "Селектор")],
        "uncheck": [("selector", "Селектор")],
        "scroll_to": [("selector", "Селектор")],
        "draw_signature": [("selector", "Canvas / область подписи")],
        "upload": [("selector", "Селектор"), ("path", "Путь к файлу")],
        "press": [("key", "Клавиша"), ("selector", "Селектор (пусто = страница)")],
        "assert_visible": [("selector", "Селектор")],
        "assert_hidden": [("selector", "Селектор")],
        "assert_text": [("selector", "Селектор"), ("value", "Текст")],
        "assert_url": [("url", "URL")],
        "wait_for": [("selector", "Селектор")],
        "wait_for_hidden": [("selector", "Селектор")],
        "wait": [("ms", "Длительность, мс")],
    }
    return specs.get(action, [])


def edit_step_dialog(parent: QWidget | None, step: dict[str, Any], *, index: int) -> dict[str, Any] | None:
    dialog = StepEditorDialog(parent, step, index=index)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.edited_step(step)
