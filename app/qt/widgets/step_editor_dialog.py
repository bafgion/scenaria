"""Dialog for editing a single scenario step."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QWidget,
)

from app.qt.dialogs import BTN_OK, ok_cancel_button_box
from app.selector_build import strategy_label

from app.step_display import ACTION_ICONS


class StepEditorDialog(QDialog):
    def __init__(self, parent: QWidget | None, step: dict[str, Any], *, index: int) -> None:
        super().__init__(parent)
        action = str(step.get("action", ""))
        icon = ACTION_ICONS.get(action, "•")
        self.setWindowTitle(f"Шаг {index + 1}")
        self._action = action
        self._fields: dict[str, QLineEdit] = {}
        self._selector_combo: QComboBox | None = None
        self._original_step = step

        layout = QFormLayout(self)
        layout.addRow(QLabel(f"{icon} {action}"))

        field_specs = _fields_for_action(action)
        candidates = self._selector_candidates(step)
        if candidates and any(key == "selector" for key, _ in field_specs):
            self._selector_combo = QComboBox(self)
            self._selector_combo.setEditable(True)
            current = str(step.get("selector", "") or "")
            for strategy, selector in candidates:
                label = strategy_label(strategy)
                self._selector_combo.addItem(f"{label}: {selector}", selector)
            index_in_combo = self._selector_combo.findData(current)
            if index_in_combo >= 0:
                self._selector_combo.setCurrentIndex(index_in_combo)
            else:
                self._selector_combo.setEditText(current)
            self._selector_combo.currentIndexChanged.connect(self._on_candidate_changed)
            layout.addRow("Селектор", self._selector_combo)

        for key, label in field_specs:
            if key == "selector" and self._selector_combo is not None:
                continue
            edit = QLineEdit(str(step.get(key, "") or ""))
            if key == "selector":
                edit.setPlaceholderText("Элемент на странице, например кнопка «Выбрать»")
            layout.addRow(label, edit)
            self._fields[key] = edit

        if not field_specs:
            layout.addRow(QLabel("Этот шаг не редактируется из диалога."))

        buttons = ok_cancel_button_box()
        ok_btn = next(btn for btn in buttons.buttons() if btn.text() == BTN_OK)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        if not field_specs:
            ok_btn.setEnabled(False)
        layout.addRow(buttons)

    @staticmethod
    def _selector_candidates(step: dict[str, Any]) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        seen: set[str] = set()
        current = str(step.get("selector", "") or "").strip()
        current_strategy = str(step.get("selectorStrategy", "") or "").strip()
        if current:
            result.append((current_strategy or "текущий", current))
            seen.add(current)
        raw_candidates = step.get("selectorCandidates")
        if isinstance(raw_candidates, list):
            for item in raw_candidates:
                if not isinstance(item, dict):
                    continue
                selector = str(item.get("selector", "") or "").strip()
                strategy = str(item.get("strategy", "") or "").strip() or "вариант"
                if not selector or selector in seen:
                    continue
                result.append((strategy, selector))
                seen.add(selector)
        return result

    def _on_candidate_changed(self, index: int) -> None:
        if self._selector_combo is None or index < 0:
            return
        data = self._selector_combo.itemData(index)
        if data:
            self._selector_combo.setEditText(str(data))

    def edited_step(self, original: dict[str, Any]) -> dict[str, Any] | None:
        if self.result() != QDialog.DialogCode.Accepted:
            return None
        step = dict(original)
        if self._selector_combo is not None:
            value = self._selector_combo.currentText().strip()
            if not value and self._action not in {"press"}:
                return None
            if value:
                step["selector"] = value
                for strategy, selector in self._selector_candidates(original):
                    if selector == value and strategy not in {"", "текущий", "вариант"}:
                        step["selectorStrategy"] = strategy
                        break
            else:
                step.pop("selector", None)
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
