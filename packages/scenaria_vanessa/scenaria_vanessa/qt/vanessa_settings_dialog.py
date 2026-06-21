"""Vanessa Automation global settings dialog."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.qt.dialogs import BTN_CANCEL, BTN_OK
from scenaria_vanessa.epf_install import default_epf_path, resolve_epf_download_url
from scenaria_vanessa.settings import load_vanessa_settings, save_vanessa_settings, validate_paths


class _EpfDownloadThread(QThread):
    done = Signal(str)
    failed = Signal(str)
    progress = Signal(int, int)

    def __init__(self, *, url: str, destination: Path, settings: dict) -> None:
        super().__init__()
        self._url = url
        self._destination = destination
        self._settings = settings

    def run(self) -> None:
        try:
            from scenaria_vanessa.epf_install import download_vanessa_epf

            path = download_vanessa_epf(
                self._destination,
                url=self._url,
                settings=self._settings,
                on_progress=lambda read, total: self.progress.emit(read, total),
            )
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
            return
        self.done.emit(str(path))


class VanessaSettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки Vanessa Automation")
        self.setMinimumWidth(560)
        self._fields: dict[str, QLineEdit] = {}
        self._settings = load_vanessa_settings()
        self._download_thread: _EpfDownloadThread | None = None

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
            ("epf_download_url", "URL загрузки Vanessa (.epf)"),
        ):
            row = QHBoxLayout()
            edit = QLineEdit(str(self._settings.get(key, "") or ""))
            self._fields[key] = edit
            row.addWidget(edit, stretch=1)
            if key == "epf_path":
                download_btn = QPushButton("Скачать")
                download_btn.clicked.connect(self._download_epf)
                row.addWidget(download_btn)
            if key in {"platform_executable", "epf_path", "runs_dir"}:
                browse = QPushButton("…")
                browse.setFixedWidth(32)
                browse.clicked.connect(lambda checked=False, k=key: self._browse(k))
                row.addWidget(browse)
            wrapper = QWidget()
            wrapper.setLayout(row)
            form.addRow(label, wrapper)
        if not self._fields["epf_path"].text().strip():
            self._fields["epf_path"].setPlaceholderText(str(default_epf_path()))
        if not self._fields["epf_download_url"].text().strip():
            self._fields["epf_download_url"].setPlaceholderText(resolve_epf_download_url(self._settings))
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

    def _download_epf(self) -> None:
        if self._download_thread is not None and self._download_thread.isRunning():
            return
        settings = self._collect()
        destination = default_epf_path()
        custom = str(settings.get("epf_path", "") or "").strip()
        if custom:
            destination = Path(custom).expanduser()
        url = resolve_epf_download_url(settings)
        self._status.setText(f"Загрузка Vanessa Automation…\n{url}")
        self._download_thread = _EpfDownloadThread(url=url, destination=destination, settings=settings)
        self._download_thread.progress.connect(self._on_download_progress)
        self._download_thread.done.connect(self._on_download_done)
        self._download_thread.failed.connect(self._on_download_failed)
        self._download_thread.start()

    def _on_download_progress(self, read: int, total: int) -> None:
        if total <= 0:
            return
        percent = int(read * 100 / total)
        self._status.setText(f"Загрузка Vanessa Automation… {percent}%")

    def _on_download_done(self, path: str) -> None:
        self._fields["epf_path"].setText(path)
        save_vanessa_settings(self._collect())
        self._status.setText(f"Обработка Vanessa загружена:\n{path}")
        QMessageBox.information(self, "Vanessa Automation", "Обработка .epf успешно загружена.")

    def _on_download_failed(self, message: str) -> None:
        self._status.setText(f"Не удалось загрузить Vanessa Automation:\n{message}")
        QMessageBox.warning(self, "Vanessa Automation", message)

    def _check_environment(self) -> None:
        issues = validate_paths(self._collect())
        if issues:
            self._status.setText("Проблемы:\n• " + "\n• ".join(issues))
        else:
            self._status.setText("Платформа и обработка VA найдены.")

    def _save(self) -> None:
        save_vanessa_settings(self._collect())
        self.accept()

    def closeEvent(self, event) -> None:  # noqa: ANN001, N802
        if self._download_thread is not None and self._download_thread.isRunning():
            self._download_thread.wait(2000)
        super().closeEvent(event)
