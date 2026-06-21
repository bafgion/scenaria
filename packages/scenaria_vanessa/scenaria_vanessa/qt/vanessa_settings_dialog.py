"""Vanessa Automation global settings dialog."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.qt.dialogs import BTN_CANCEL, BTN_OK
from scenaria_vanessa.settings import load_vanessa_settings, save_vanessa_settings, validate_paths


class VanessaSettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки Vanessa Automation")
        self.setMinimumWidth(560)
        self._fields: dict[str, QLineEdit] = {}
        self._settings = load_vanessa_settings()

        root = QVBoxLayout(self)
        form = QFormLayout()
        for key, label in (
            ("platform_executable", "Платформа 1С (1cv8c.exe)"),
            ("epf_path", "Обработка Vanessa (.epf)"),
            ("ib_connection_string", "Строка подключения ИБ"),
            ("user", "Пользователь (/N)"),
            ("password", "Пароль (/P)"),
            ("runs_dir", "Каталог прогонов (пусто = по умолчанию)"),
            ("project_base_params", "Base VAParams в проекте"),
            ("install_url", "URL zip add-on (offline mirror)"),
        ):
            row = QHBoxLayout()
            edit = QLineEdit(str(self._settings.get(key, "") or ""))
            self._fields[key] = edit
            row.addWidget(edit, stretch=1)
            if key in {"platform_executable", "epf_path", "runs_dir"}:
                browse = QPushButton("…")
                browse.setFixedWidth(32)
                browse.clicked.connect(lambda checked=False, k=key: self._browse(k))
                row.addWidget(browse)
            wrapper = QWidget()
            wrapper.setLayout(row)
            form.addRow(label, wrapper)
        root.addLayout(form)

        self._timeout = QSpinBox()
        self._timeout.setRange(60, 86400)
        self._timeout.setValue(int(self._settings.get("process_timeout_sec", 3600) or 3600))
        form.addRow("Таймаут процесса (сек)", self._timeout)

        self._report_junit = QCheckBox("JUnit по умолчанию")
        self._report_junit.setChecked(bool(self._settings.get("report_junit", True)))
        form.addRow("Отчёты", self._report_junit)
        self._report_allure = QCheckBox("Allure по умолчанию")
        self._report_allure.setChecked(bool(self._settings.get("report_allure", False)))
        form.addRow("", self._report_allure)
        self._fields["allure_cli_path"] = QLineEdit(str(self._settings.get("allure_cli_path", "allure") or "allure"))
        form.addRow("Allure CLI", self._fields["allure_cli_path"])

        self._status = QLabel("")
        self._status.setWordWrap(True)
        root.addWidget(self._status)

        buttons = QHBoxLayout()
        check_btn = QPushButton("Проверить окружение")
        check_btn.clicked.connect(self._check_environment)
        buttons.addWidget(check_btn)
        buttons.addStretch()
        ok_btn = QPushButton(BTN_OK)
        ok_btn.clicked.connect(self._save)
        cancel_btn = QPushButton(BTN_CANCEL)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        root.addLayout(buttons)

    def _browse(self, key: str) -> None:
        if key == "epf_path":
            path, _ = QFileDialog.getOpenFileName(self, "Обработка Vanessa", "", "EPF (*.epf);;All (*.*)")
        else:
            path = QFileDialog.getExistingDirectory(self, "Каталог") if key == "runs_dir" else QFileDialog.getOpenFileName(
                self, "Исполняемый файл", "", "EXE (*.exe);;All (*.*)"
            )[0]
        if path:
            self._fields[key].setText(path)

    def _collect(self) -> dict:
        payload = dict(self._settings)
        for key, edit in self._fields.items():
            payload[key] = edit.text().strip()
        payload["process_timeout_sec"] = int(self._timeout.value())
        payload["report_junit"] = self._report_junit.isChecked()
        payload["report_allure"] = self._report_allure.isChecked()
        return payload

    def _check_environment(self) -> None:
        issues = validate_paths(self._collect())
        if issues:
            self._status.setText("Проблемы:\n• " + "\n• ".join(issues))
        else:
            self._status.setText("Платформа и обработка VA найдены.")

    def _save(self) -> None:
        save_vanessa_settings(self._collect())
        self.accept()
