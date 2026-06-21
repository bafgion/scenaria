"""Bottom panel for structured selector validation results."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.selector_validate import StepValidateResult, format_validate_report_text
from app.step_display import format_step_table_cells

_STATUS_ICONS = {
    "ok": "✓",
    "fragile": "⚠",
    "not_found": "✗",
    "ambiguous": "✗",
    "hidden": "✗",
    "error": "✗",
    "no_selector": "✗",
    "skipped": "—",
}

_STATUS_LABELS = {
    "ok": "OK",
    "fragile": "Хрупкий",
    "not_found": "Не найден",
    "ambiguous": "Несколько",
    "hidden": "Скрыт",
    "error": "Ошибка",
    "no_selector": "Нет селектора",
    "skipped": "Пропуск",
}


class ValidateResultsPanel(QWidget):
    step_focus_requested = Signal(int)  # 1-based step index

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._results: list[dict[str, Any]] = []
        self._issues: list[str] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        header.setContentsMargins(8, 4, 8, 0)
        self._summary = QLabel("")
        header.addWidget(self._summary, stretch=1)
        copy_btn = QPushButton("Копировать отчёт")
        copy_btn.clicked.connect(self._copy_report)
        header.addWidget(copy_btn)
        layout.addLayout(header)

        self._table = QTableWidget(0, 5, self)
        self._table.setHorizontalHeaderLabels(["#", "Действие", "Селектор", "Статус", "Сообщение"])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        header_view = self._table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.cellDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._table)

    def show_results(self, payload: dict[str, Any]) -> None:
        self._issues = list(payload.get("issues") or [])
        self._results = list(payload.get("results") or [])
        blocking = len(self._issues)
        checked = sum(1 for item in self._results if item.get("status") not in {"skipped"})
        ok = sum(1 for item in self._results if item.get("status") in {"ok", "fragile"})
        if blocking:
            self._summary.setText(f"Проверено шагов: {checked} · проблем: {blocking}")
        else:
            self._summary.setText(f"Проверено шагов: {checked} · OK: {ok}")

        self._table.setRowCount(0)
        for item in self._results:
            status = str(item.get("status", "") or "")
            if status == "skipped":
                continue
            row = self._table.rowCount()
            self._table.insertRow(row)
            step_index = int(item.get("step_index", row + 1))
            action = str(item.get("action", "") or "")
            selector = str(item.get("selector", "") or "")
            message = str(item.get("message", "") or "")
            label, target, _value = format_step_table_cells(
                {
                    "action": action,
                    "selector": selector,
                    "url": selector if action in {"goto", "assert_url"} else "",
                }
            )
            display_target = target or selector or "—"
            status_text = f"{_STATUS_ICONS.get(status, '•')} {_STATUS_LABELS.get(status, status)}"

            index_item = QTableWidgetItem(str(step_index))
            index_item.setData(Qt.ItemDataRole.UserRole, step_index)
            self._table.setItem(row, 0, index_item)
            self._table.setItem(row, 1, QTableWidgetItem(label))
            self._table.setItem(row, 2, QTableWidgetItem(display_target))
            self._table.setItem(row, 3, QTableWidgetItem(status_text))
            self._table.setItem(row, 4, QTableWidgetItem(message))

    def _on_double_click(self, row: int, _column: int) -> None:
        item = self._table.item(row, 0)
        if item is None:
            return
        step_index = item.data(Qt.ItemDataRole.UserRole)
        if step_index:
            self.step_focus_requested.emit(int(step_index))

    def _copy_report(self) -> None:
        results = [StepValidateResult(**item) for item in self._results if isinstance(item, dict)]
        text = format_validate_report_text(results, issues=self._issues)
        QGuiApplication.clipboard().setText(text)

    def results_as_payload(self) -> dict[str, Any]:
        return {"issues": list(self._issues), "results": list(self._results)}
