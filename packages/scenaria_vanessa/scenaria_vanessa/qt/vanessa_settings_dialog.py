"""Vanessa Automation global settings dialog."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.qt.dialogs import BTN_CANCEL, BTN_OK
from app.update.progress import format_bytes
from scenaria_vanessa.epf_install import default_epf_path, resolve_epf_download_url
from scenaria_vanessa.settings import load_vanessa_settings, save_vanessa_settings, validate_paths

_PHASE_LABELS = {
    "resolve": "Поиск релиза…",
    "download": "Скачивание…",
    "extract": "Распаковка…",
}


class _EpfDownloadThread(QThread):
    done = Signal(str)
    failed = Signal(str)
    progress = Signal(int, int)
    phase = Signal(str)

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
                on_phase=lambda name: self.phase.emit(name),
            )
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
            return
        self.done.emit(str(path))


class VanessaSettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки Vanessa Automation")
        self.setMinimumSize(440, 320)
        self.resize(520, 460)
        self._fields: dict[str, QLineEdit] = {}
        self._settings = load_vanessa_settings()
        self._download_thread: _EpfDownloadThread | None = None
        self._download_controls: list[QWidget] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        scroll = QScrollArea()
        scroll.setProperty("role", "settings-scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        content = QWidget()
        content.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 4, 0)
        content_layout.setSpacing(12)

        content_layout.addWidget(self._build_install_card())
        content_layout.addWidget(self._build_form())
        content_layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

        self._status = QLabel("")
        self._status.setWordWrap(True)
        self._status.setStyleSheet("color: #858585;")
        root.addWidget(self._status)

        buttons = QHBoxLayout()
        self._check_btn = QPushButton("Проверить окружение")
        self._check_btn.clicked.connect(self._check_environment)
        buttons.addWidget(self._check_btn)
        buttons.addStretch()
        self._ok_btn = QPushButton(BTN_OK)
        self._ok_btn.clicked.connect(self._save)
        self._cancel_btn = QPushButton(BTN_CANCEL)
        self._cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self._ok_btn)
        buttons.addWidget(self._cancel_btn)
        root.addLayout(buttons)

        self._download_controls.extend(
            [self._ok_btn, self._cancel_btn, self._check_btn, self._install_btn]
        )
        self._refresh_epf_status()

    def _build_install_card(self) -> QWidget:
        card = QFrame()
        card.setProperty("role", "settings-section")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        title = QLabel("Обработка Vanessa Automation")
        title.setStyleSheet("font-size: 14px; font-weight: 600;")
        layout.addWidget(title)

        hint = QLabel(
            "Скачивает последний релиз с GitHub (архив single.zip) и сохраняет .epf локально."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #858585;")
        layout.addWidget(hint)

        self._epf_status = QLabel("")
        self._epf_status.setWordWrap(True)
        layout.addWidget(self._epf_status)

        self._install_phase = QLabel("")
        self._install_phase.setStyleSheet("font-weight: 600;")
        layout.addWidget(self._install_phase)

        self._install_bar = QProgressBar()
        self._install_bar.setRange(0, 100)
        self._install_bar.setValue(0)
        self._install_bar.setTextVisible(True)
        self._install_bar.setFixedHeight(22)
        self._install_bar.hide()
        layout.addWidget(self._install_bar)

        self._install_detail = QLabel("")
        self._install_detail.setWordWrap(True)
        self._install_detail.setStyleSheet("color: #858585;")
        layout.addWidget(self._install_detail)

        row = QHBoxLayout()
        self._install_btn = QPushButton("Скачать и установить")
        self._install_btn.setDefault(True)
        self._install_btn.clicked.connect(self._download_epf)
        row.addWidget(self._install_btn)
        row.addStretch()
        layout.addLayout(row)
        return card

    def _build_form(self) -> QWidget:
        panel = QWidget()
        form = QFormLayout(panel)
        form.setContentsMargins(0, 0, 0, 0)
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
            if key in {"platform_executable", "epf_path", "runs_dir"}:
                browse = QPushButton("…")
                browse.setFixedWidth(32)
                browse.clicked.connect(lambda checked=False, k=key: self._browse(k))
                row.addWidget(browse)
                if key == "epf_path":
                    self._download_controls.append(browse)
            wrapper = QWidget()
            wrapper.setLayout(row)
            form.addRow(label, wrapper)
        if not self._fields["epf_path"].text().strip():
            self._fields["epf_path"].setPlaceholderText(str(default_epf_path()))
        if not self._fields["epf_download_url"].text().strip():
            try:
                placeholder_url = resolve_epf_download_url(self._settings)
            except OSError:
                placeholder_url = "https://github.com/Pr-Mex/vanessa-automation/releases/latest"
            self._fields["epf_download_url"].setPlaceholderText(placeholder_url)

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
        return panel

    def _current_epf_path(self) -> Path:
        custom = self._fields["epf_path"].text().strip()
        if custom:
            return Path(custom).expanduser()
        return default_epf_path()

    def _refresh_epf_status(self) -> None:
        path = self._current_epf_path()
        if path.is_file() and path.stat().st_size > 0:
            self._epf_status.setText(f"Установлена: {path}")
            self._epf_status.setStyleSheet("color: #4ec9b0;")
            self._install_btn.setText("Переустановить")
        else:
            self._epf_status.setText("Не установлена — укажите путь или скачайте с GitHub.")
            self._epf_status.setStyleSheet("color: #ce9178;")
            self._install_btn.setText("Скачать и установить")

    def _set_download_busy(self, busy: bool) -> None:
        for widget in self._download_controls:
            widget.setEnabled(not busy)
        if busy:
            self._install_bar.show()
            self._install_bar.setValue(0)
            self._install_bar.setFormat("0 %")
        else:
            self._install_bar.hide()
            self._install_phase.clear()
            self._install_detail.clear()

    def _browse(self, key: str) -> None:
        if key == "epf_path":
            path, _ = QFileDialog.getOpenFileName(self, "Обработка Vanessa", "", "EPF (*.epf);;All (*.*)")
        else:
            path = QFileDialog.getExistingDirectory(self, "Каталог") if key == "runs_dir" else QFileDialog.getOpenFileName(
                self, "Исполняемый файл", "", "EXE (*.exe);;All (*.*)"
            )[0]
        if path:
            self._fields[key].setText(path)
            if key == "epf_path":
                self._refresh_epf_status()

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
        destination = self._current_epf_path()
        self._set_download_busy(True)
        self._install_phase.setText(_PHASE_LABELS["resolve"])
        self._install_detail.setText("Определение URL последнего релиза…")
        try:
            url = resolve_epf_download_url(settings)
        except OSError as exc:
            self._set_download_busy(False)
            self._status.setText(str(exc))
            QMessageBox.warning(self, "Vanessa Automation", str(exc))
            return

        self._install_detail.setText(url)
        self._download_thread = _EpfDownloadThread(url=url, destination=destination, settings=settings)
        self._download_thread.phase.connect(self._on_download_phase)
        self._download_thread.progress.connect(self._on_download_progress)
        self._download_thread.done.connect(self._on_download_done)
        self._download_thread.failed.connect(self._on_download_failed)
        self._download_thread.start()

    def _on_download_phase(self, phase: str) -> None:
        self._install_phase.setText(_PHASE_LABELS.get(phase, phase))
        if phase == "extract":
            self._install_bar.setRange(0, 0)
            self._install_detail.setText("Извлечение .epf из архива…")

    def _on_download_progress(self, read: int, total: int) -> None:
        self._install_phase.setText(_PHASE_LABELS["download"])
        if self._install_bar.maximum() == 0:
            self._install_bar.setRange(0, 100)
        if total <= 0:
            self._install_bar.setRange(0, 0)
            self._install_detail.setText(f"Скачано {format_bytes(read)}")
            return
        percent = int(read * 100 / total)
        self._install_bar.setValue(percent)
        self._install_bar.setFormat(f"{percent} %")
        self._install_detail.setText(f"{format_bytes(read)} / {format_bytes(total)}")

    def _on_download_done(self, path: str) -> None:
        self._set_download_busy(False)
        self._fields["epf_path"].setText(path)
        save_vanessa_settings(self._collect())
        self._refresh_epf_status()
        self._status.setText(f"Обработка Vanessa загружена: {path}")
        self._install_bar.setRange(0, 100)
        self._install_bar.setValue(100)
        self._install_bar.setFormat("100 %")
        QMessageBox.information(self, "Vanessa Automation", "Обработка .epf успешно загружена.")

    def _on_download_failed(self, message: str) -> None:
        self._set_download_busy(False)
        self._refresh_epf_status()
        self._status.setText(f"Не удалось загрузить Vanessa Automation: {message}")
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
