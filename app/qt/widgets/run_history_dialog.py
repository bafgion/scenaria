"""Dialog showing run history for a `.feature` file."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.qt.dialogs import BTN_CLOSE
from app.run_display import format_duration, format_run_at
from app.run_status_store import RunHistoryEntry, get_run_history


class RunHistoryDialog(QDialog):
    def __init__(self, parent: QWidget | None, path: Path) -> None:
        super().__init__(parent)
        self._path = path.resolve()
        self.setWindowTitle(f"История прогонов — {self._path.name}")
        self.setMinimumSize(720, 320)

        root = QVBoxLayout(self)
        self._table = QTableWidget(0, 6, self)
        self._table.setHorizontalHeaderLabels(
            ["Когда", "Runner", "Результат", "Длительность", "Шаг", "Отчёт"]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self._table.cellDoubleClicked.connect(self._open_report_for_row)
        root.addWidget(self._table)

        buttons = QHBoxLayout()
        self._open_report_btn = QPushButton("Открыть отчёт")
        self._open_report_btn.clicked.connect(self._open_selected_report)
        buttons.addWidget(self._open_report_btn)
        self._open_run_dir_btn = QPushButton("Каталог прогона")
        self._open_run_dir_btn.clicked.connect(self._open_selected_run_dir)
        buttons.addWidget(self._open_run_dir_btn)
        buttons.addStretch()
        close_btn = QPushButton(BTN_CLOSE)
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        root.addLayout(buttons)

        self._entries: list[RunHistoryEntry] = []
        self._populate(get_run_history(self._path))
        self._table.itemSelectionChanged.connect(self._update_buttons)
        self._update_buttons()

    def _populate(self, entries: list[RunHistoryEntry]) -> None:
        self._entries = list(entries)
        self._table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            when = QTableWidgetItem(format_run_at(entry.at))
            when.setData(Qt.ItemDataRole.UserRole, row)
            self._table.setItem(row, 0, when)

            runner = QTableWidgetItem(entry.runner or "playwright")
            self._table.setItem(row, 1, runner)

            result = QTableWidgetItem("OK" if entry.success else "FAIL")
            if not entry.success:
                result.setToolTip(entry.message)
            self._table.setItem(row, 2, result)

            duration = QTableWidgetItem(
                format_duration(entry.duration_ms) if entry.duration_ms else "—"
            )
            self._table.setItem(row, 3, duration)

            failed = QTableWidgetItem(
                str(entry.failed_step) if entry.failed_step is not None else "—"
            )
            self._table.setItem(row, 4, failed)

            report_label = "—"
            if entry.report_path:
                report_label = Path(entry.report_path).name
            elif entry.run_dir:
                report_label = Path(entry.run_dir).name
            report = QTableWidgetItem(report_label)
            tooltip = entry.report_path or entry.run_dir or ""
            if tooltip:
                report.setToolTip(tooltip)
            self._table.setItem(row, 5, report)

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

    def _update_buttons(self) -> None:
        row = self._selected_row()
        self._open_report_btn.setEnabled(
            row is not None and self._report_path_for_row(row or -1) is not None
        )
        self._open_run_dir_btn.setEnabled(row is not None and self._run_dir_for_row(row or -1) is not None)

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
