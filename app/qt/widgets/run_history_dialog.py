"""Dialog showing run history for a `.feature` file."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QWidget

from app.qt.dialog_buttons import BTN_CLOSE
from app.qt.icons import toolbar_icon
from app.qt.labels import caption_label, dialog_title_label, muted_label
from app.qt.theme import COLOR_ERROR, COLOR_SUCCESS
from app.qt.widgets.base_dialog import BaseAppDialog, dialog_action_button
from app.run_display import format_duration, format_run_at
from app.run_result_display import (
    brief_error_message,
    format_failed_step_label,
    format_runner_label,
    format_run_status_text,
    summarize_run_history,
)
from app.run_status_store import RunHistoryEntry, get_run_history


def _status_color(success: bool) -> QColor:
    return QColor(COLOR_SUCCESS if success else COLOR_ERROR)


class RunHistoryDialog(BaseAppDialog):
    def __init__(self, parent: QWidget | None, path: Path) -> None:
        super().__init__(parent, title=f"История прогонов — {path.name}", min_size=(760, 400))
        self._path = path.resolve()

        title = dialog_title_label(self._path.name)
        self.content_layout.addWidget(title)

        subtitle = muted_label(str(self._path.parent), word_wrap=True)
        self.content_layout.addWidget(subtitle)

        self._summary = QLabel("")
        self._summary.setWordWrap(True)
        self.content_layout.addWidget(self._summary)

        self._empty = QLabel("Прогонов пока не было.\nЗапустите сценарий — результаты появятся здесь.")
        self._empty.setProperty("role", "run-history-empty")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setWordWrap(True)
        self.content_layout.addWidget(self._empty)

        self._table = QTableWidget(0, 5, self)
        self._table.setProperty("role", "run-results-table")
        self._table.setHorizontalHeaderLabels(
            ["Когда", "Движок", "Результат", "Длительность", "Где упало"]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.cellDoubleClicked.connect(self._open_report_for_row)
        self.content_layout.addWidget(self._table)

        self._detail = QLabel("")
        self._detail.setWordWrap(True)
        self._detail.setProperty("role", "run-history-detail")
        self._detail.hide()
        self.content_layout.addWidget(self._detail)

        self.content_layout.addWidget(
            caption_label("Дважды щёлкните строку, чтобы открыть HTML-отчёт или каталог прогона.")
        )

        self._open_report_btn = dialog_action_button("Открыть отчёт")
        self._open_report_btn.setIcon(toolbar_icon("feature"))
        self._open_report_btn.clicked.connect(self._open_selected_report)
        self._open_run_dir_btn = dialog_action_button("Каталог прогона")
        self._open_run_dir_btn.setIcon(toolbar_icon("explorer"))
        self._open_run_dir_btn.clicked.connect(self._open_selected_run_dir)
        close_btn = dialog_action_button(BTN_CLOSE)
        close_btn.clicked.connect(self.accept)
        self.add_button_row(self._open_report_btn, self._open_run_dir_btn, close_btn)

        self._entries: list[RunHistoryEntry] = []
        self._populate(get_run_history(self._path))
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._on_selection_changed()

    def _populate(self, entries: list[RunHistoryEntry]) -> None:
        self._entries = list(entries)
        self._summary.setText(summarize_run_history(entries))
        has_entries = bool(entries)
        self._empty.setVisible(not has_entries)
        self._table.setVisible(has_entries)
        self._table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            when = QTableWidgetItem(format_run_at(entry.at))
            when.setData(Qt.ItemDataRole.UserRole, row)
            self._table.setItem(row, 0, when)

            runner = QTableWidgetItem(format_runner_label(entry.runner))
            self._table.setItem(row, 1, runner)

            result = QTableWidgetItem(format_run_status_text(entry.success))
            result.setForeground(_status_color(entry.success))
            if entry.message:
                result.setToolTip(entry.message)
            self._table.setItem(row, 2, result)

            duration = QTableWidgetItem(
                format_duration(entry.duration_ms) if entry.duration_ms else "—"
            )
            self._table.setItem(row, 3, duration)

            failed = QTableWidgetItem(format_failed_step_label(entry.failed_step))
            if entry.message and not entry.success:
                failed.setToolTip(brief_error_message(entry.message))
            self._table.setItem(row, 4, failed)

            report_bits: list[str] = []
            if entry.report_path:
                report_bits.append(f"Отчёт: {entry.report_path}")
            if entry.run_dir:
                report_bits.append(f"Каталог: {entry.run_dir}")
            if report_bits:
                when.setToolTip("\n".join(report_bits))

        if entries:
            self._table.selectRow(0)

    def _selected_row(self) -> int | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        return int(rows[0].row())

    def _report_path_for_row(self, row: int) -> Path | None:
        if row < 0 or row >= len(self._entries):
            return None
        raw = self._entries[row].report_path
        if not raw:
            return None
        path = Path(raw)
        return path if path.is_file() else None

    def _run_dir_for_row(self, row: int) -> Path | None:
        if row < 0 or row >= len(self._entries):
            return None
        raw = self._entries[row].run_dir
        if not raw:
            return None
        path = Path(raw)
        return path if path.is_dir() else None

    def _on_selection_changed(self) -> None:
        row = self._selected_row()
        self._open_report_btn.setEnabled(
            row is not None and self._report_path_for_row(row or -1) is not None
        )
        self._open_run_dir_btn.setEnabled(row is not None and self._run_dir_for_row(row or -1) is not None)
        if row is None or row >= len(self._entries):
            self._detail.hide()
            return
        entry = self._entries[row]
        if entry.success or not entry.message:
            self._detail.hide()
            return
        self._detail.setText(f"Ошибка: {entry.message.strip()}")
        self._detail.show()

    def _open_report_for_row(self, row: int, _column: int) -> None:
        path = self._report_path_for_row(row)
        if path is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))
        else:
            run_dir = self._run_dir_for_row(row)
            if run_dir is not None:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(run_dir.resolve())))

    def _open_selected_report(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        self._open_report_for_row(row, 0)

    def _open_selected_run_dir(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        run_dir = self._run_dir_for_row(row)
        if run_dir is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(run_dir.resolve())))


def open_run_history_dialog(parent: QWidget | None, path: Path) -> None:
    dialog = RunHistoryDialog(parent, path)
    dialog.exec()
