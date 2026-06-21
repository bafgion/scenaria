"""Play results output."""



from __future__ import annotations



from pathlib import Path



from PySide6.QtCore import QUrl

from PySide6.QtGui import QDesktopServices

from PySide6.QtWidgets import QHBoxLayout, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget



from app.qt.fonts import editor_font

from app.run_display import format_duration





class ResultsPanel(QWidget):

    def __init__(self, parent: QWidget | None = None) -> None:

        super().__init__(parent)

        self._on_jump = None

        self._on_history = None

        self._on_rerun_failed = None

        self._on_open_allure = None

        self._html_report_path: Path | None = None

        self._feature_path: Path | None = None

        self._allure_dir: Path | None = None

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)



        header = QHBoxLayout()

        header.setContentsMargins(8, 4, 8, 0)

        self.open_report_btn = QPushButton("Открыть HTML-отчёт")

        self.open_report_btn.hide()

        self.open_report_btn.clicked.connect(self._open_report)

        header.addWidget(self.open_report_btn)

        self.history_btn = QPushButton("История прогонов")

        self.history_btn.hide()

        self.history_btn.clicked.connect(self._open_history)

        header.addWidget(self.history_btn)

        self.allure_btn = QPushButton("Открыть Allure")

        self.allure_btn.hide()

        self.allure_btn.clicked.connect(self._open_allure)

        header.addWidget(self.allure_btn)

        self.rerun_failed_btn = QPushButton("Перезапустить упавшие")

        self.rerun_failed_btn.hide()

        self.rerun_failed_btn.clicked.connect(self._rerun_failed)

        header.addWidget(self.rerun_failed_btn)

        header.addStretch()

        self.jump_btn = QPushButton("К ошибке")

        self.jump_btn.hide()

        self.jump_btn.clicked.connect(self._jump)

        header.addWidget(self.jump_btn)

        layout.addLayout(header)



        self.editor = QPlainTextEdit()

        self.editor.setReadOnly(True)

        self.editor.setProperty("role", "mono-panel")

        self.editor.setFont(editor_font())

        layout.addWidget(self.editor)



    def set_jump_handler(self, handler) -> None:

        self._on_jump = handler



    def set_history_handler(self, handler) -> None:

        self._on_history = handler



    def set_rerun_failed_handler(self, handler) -> None:

        self._on_rerun_failed = handler



    def set_open_allure_handler(self, handler) -> None:

        self._on_open_allure = handler



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



    def show_results(self, payload: dict, *, has_failed_step: bool) -> None:

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

        duration_ms = int(payload.get("duration_ms", 0))

        lines = [

            f"Длительность: {format_duration(duration_ms)}",

        ]

        if payload.get("runner"):

            lines.append(f"Runner: {payload.get('runner')}")

        if payload.get("run_dir"):

            lines.append(f"Каталог прогона: {payload.get('run_dir')}")

        lines.append(str(payload.get("comparison", "")))

        suite_index = payload.get("suite_html_index")

        if suite_index:

            lines.append(f"Сводный отчёт: {suite_index}")

        if self._html_report_path:

            lines.append(f"HTML-отчёт: {self._html_report_path}")

        if self._allure_dir:

            lines.append(f"Allure: {self._allure_dir}")

        suite_cases = payload.get("suite_cases")

        if suite_cases:

            lines.append("")

            lines.append("Детали:")

            for case in suite_cases:

                path = case.get("path")

                label = path.name if hasattr(path, "name") else str(case.get("name", "?"))

                if case.get("success"):

                    lines.append(f"  OK  {label}")

                else:

                    brief = str(case.get("message", "")).splitlines()[0][:120]

                    lines.append(f"  FAIL {label}: {brief}")

        lines.extend(["", "Журнал:", *list(payload.get("log_lines", []))])

        self.editor.setPlainText("\n".join(lines))

        self.jump_btn.setVisible(has_failed_step and not suite_cases)

