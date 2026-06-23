"""Play results output."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.qt.icons import toolbar_icon
from app.qt.theme import COLOR_ERROR, COLOR_SUCCESS
from app.run_result_display import (
    brief_error_message,
    format_run_status_text,
    format_single_run_summary,
    summarize_suite_cases,
)


def _status_color(success: bool) -> QColor:
    return QColor(COLOR_SUCCESS if success else COLOR_ERROR)


class ResultsPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "results-panel")
        self._on_jump = None
        self._on_history = None
        self._on_rerun_failed = None
        self._on_open_allure = None
        self._html_report_path: Path | None = None
        self._feature_path: Path | None = None
        self._allure_dir: Path | None = None
        self._live_mode = False
        self._rendered_case_count = 0
        self._suite_cases: list[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(8, 6, 8, 4)
        self.open_report_btn = QPushButton("HTML-отчёт")
        self.open_report_btn.setIcon(toolbar_icon("feature"))
        self.open_report_btn.hide()
        self.open_report_btn.setToolTip("Открыть HTML-отчёт последнего прогона")
        self.open_report_btn.clicked.connect(self._open_report)
        header.addWidget(self.open_report_btn)

        self.history_btn = QPushButton("История")
        self.history_btn.setIcon(toolbar_icon("results"))
        self.history_btn.hide()
        self.history_btn.setToolTip("История прогонов этого сценария")
        self.history_btn.clicked.connect(self._open_history)
        header.addWidget(self.history_btn)

        self.allure_btn = QPushButton("Allure")
        self.allure_btn.setIcon(toolbar_icon("results"))
        self.allure_btn.hide()
        self.allure_btn.setToolTip("Открыть отчёт Allure")
        self.allure_btn.clicked.connect(self._open_allure)
        header.addWidget(self.allure_btn)

        self.rerun_failed_btn = QPushButton("Перезапустить упавшие")
        self.rerun_failed_btn.hide()
        self.rerun_failed_btn.clicked.connect(self._rerun_failed)
        header.addWidget(self.rerun_failed_btn)
        header.addStretch()

        self.jump_btn = QPushButton("К ошибке")
        self.jump_btn.hide()
        self.jump_btn.setToolTip("Перейти к шагу с ошибкой в редакторе")
        self.jump_btn.clicked.connect(self._jump)
        header.addWidget(self.jump_btn)
        layout.addLayout(header)

        self._summary = QLabel("")
        self._summary.setWordWrap(True)
        self._summary.setContentsMargins(8, 0, 8, 4)
        self._summary.setProperty("role", "results-summary")

        self._cases_table = QTableWidget(0, 3)
        self._cases_table.setProperty("role", "run-results-table")
        self._cases_table.setHorizontalHeaderLabels(["Сценарий", "Результат", "Сообщение"])
        self._cases_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._cases_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._cases_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._cases_table.setAlternatingRowColors(True)
        self._cases_table.verticalHeader().setVisible(False)
        header_view = self._cases_table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._cases_table.itemSelectionChanged.connect(self._on_case_selection_changed)

        self._case_detail = QLabel("")
        self._case_detail.setWordWrap(True)
        self._case_detail.setContentsMargins(8, 0, 8, 4)
        self._case_detail.setProperty("role", "run-history-detail")
        self._case_detail.hide()

        self._comparison = QLabel("")
        self._comparison.setWordWrap(True)
        self._comparison.setContentsMargins(8, 0, 8, 8)
        self._comparison.setProperty("muted", True)
        self._comparison.hide()

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(4)
        body_layout.addWidget(self._summary)
        body_layout.addWidget(self._cases_table)
        body_layout.addWidget(self._case_detail)
        body_layout.addWidget(self._comparison)
        body_layout.addStretch()
        layout.addWidget(body)

    def set_jump_handler(self, handler) -> None:
        self._on_jump = handler

    def set_history_handler(self, handler) -> None:
        self._on_history = handler

    def set_rerun_failed_handler(self, handler) -> None:
        self._on_rerun_failed = handler

    def set_open_allure_handler(self, handler) -> None:
        self._on_open_allure = handler

    def begin_live_suite(self, *, total_hint: int = 0) -> None:
        self._live_mode = True
        self._rendered_case_count = 0
        self._suite_cases = []
        self._cases_table.setRowCount(0)
        self._cases_table.show()
        self._case_detail.hide()
        hint = f" из ~{total_hint}" if total_hint > 0 else ""
        self._summary.setText(f"Прогон выполняется… загружено 0 сценариев{hint}")
        self.rerun_failed_btn.hide()
        self.open_report_btn.hide()

    def update_suite_cases(self, cases: list[dict]) -> None:
        if not cases:
            return
        self._suite_cases = list(cases)
        previous = self._rendered_case_count
        row_count = len(cases)
        if row_count < self._cases_table.rowCount():
            self._cases_table.setRowCount(row_count)
        elif row_count > self._cases_table.rowCount():
            self._cases_table.setRowCount(row_count)

        start = 0 if row_count < previous else previous
        for row in range(start, row_count):
            self._set_case_row(row, cases[row])

        if row_count > 0 and row_count <= previous:
            self._set_case_row(row_count - 1, cases[-1])

        self._rendered_case_count = row_count
        self._summary.setText(summarize_suite_cases(cases, live=self._live_mode))
        self._on_case_selection_changed()

    def _set_case_row(self, row: int, case: dict) -> None:
        path = case.get("path")
        label = path.name if hasattr(path, "name") else str(case.get("name", "?"))
        success = bool(case.get("success"))
        status = format_run_status_text(success)
        brief = brief_error_message(str(case.get("message", "")))
        values = (label, status, brief)
        for column, text in enumerate(values):
            item = self._cases_table.item(row, column)
            if item is None:
                item = QTableWidgetItem(text)
                self._cases_table.setItem(row, column, item)
            else:
                item.setText(text)
            if column == 1:
                item.setForeground(_status_color(success))
            if column == 2 and case.get("message"):
                item.setToolTip(str(case.get("message", "")))

    def _on_case_selection_changed(self) -> None:
        rows = self._cases_table.selectionModel().selectedRows()
        if not rows or not self._suite_cases:
            self._case_detail.hide()
            return
        row = int(rows[0].row())
        if row < 0 or row >= len(self._suite_cases):
            self._case_detail.hide()
            return
        case = self._suite_cases[row]
        if case.get("success") or not case.get("message"):
            self._case_detail.hide()
            return
        self._case_detail.setText(f"Ошибка: {str(case.get('message', '')).strip()}")
        self._case_detail.show()

    def _jump(self) -> None:
        if self._on_jump:
            self._on_jump()

    def _open_report(self) -> None:
        if self._html_report_path and self._html_report_path.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._html_report_path.resolve())))

    def _open_history(self) -> None:
        if self._on_history and self._feature_path is not None:
            self._on_history(self._feature_path)

    def _open_allure(self) -> None:
        if self._on_open_allure:
            self._on_open_allure(self._allure_dir)
        elif self._allure_dir and self._allure_dir.is_dir():
            from scenaria_vanessa.allure_helpers import open_allure_directory

            open_allure_directory(self._allure_dir)

    def _rerun_failed(self) -> None:
        if self._on_rerun_failed:
            self._on_rerun_failed()

    def latest_report_hints(self) -> dict[str, str | None]:
        html = str(self._html_report_path) if self._html_report_path and self._html_report_path.is_file() else None
        allure = str(self._allure_dir) if self._allure_dir and self._allure_dir.is_dir() else None
        return {
            "html_report_path": html,
            "suite_html_index": html,
            "allure_dir": allure,
        }

    def _show_comparison(self, payload: dict) -> None:
        comparison = str(payload.get("comparison", "") or "").strip()
        if comparison:
            self._comparison.setText(comparison)
            self._comparison.show()
        else:
            self._comparison.clear()
            self._comparison.hide()

    def show_results(self, payload: dict, *, has_failed_step: bool) -> None:
        self._live_mode = False
        report_path = payload.get("html_report_path")
        self._html_report_path = Path(str(report_path)) if report_path else None
        feature_raw = payload.get("feature_path")
        self._feature_path = Path(str(feature_raw)) if feature_raw else None
        allure_raw = payload.get("allure_dir")
        self._allure_dir = Path(str(allure_raw)) if allure_raw else None
        self.open_report_btn.setVisible(
            self._html_report_path is not None and self._html_report_path.is_file()
        )
        self.history_btn.setVisible(self._feature_path is not None and self._on_history is not None)
        self.allure_btn.setVisible(self._allure_dir is not None and self._allure_dir.is_dir())
        self.rerun_failed_btn.setVisible(bool(payload.get("can_rerun_failed")) and self._on_rerun_failed is not None)

        suite_cases = list(payload.get("suite_cases") or [])
        self._suite_cases = suite_cases
        if suite_cases:
            self._cases_table.show()
            self.update_suite_cases(suite_cases)
        else:
            self._cases_table.setRowCount(0)
            self._cases_table.hide()
            self._rendered_case_count = 0
            self._case_detail.hide()
            self._summary.setText(format_single_run_summary(payload))
            success = bool(payload.get("success"))
            self._summary.setProperty("success", success)
            self._summary.style().unpolish(self._summary)
            self._summary.style().polish(self._summary)

        self._show_comparison(payload)
        self.jump_btn.setVisible(has_failed_step and not suite_cases)
