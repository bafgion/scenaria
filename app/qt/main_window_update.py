"""Auto-update UI flow extracted from MainWindow (T2-1)."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QMessageBox

from app.brand import BRAND_NAME
from app.qt.dialogs import BTN_OK, alert
from app.qt.update_ui import UpdateCheckRunner, UpdateDownloadRunner, current_version_label
from app.qt.widgets.update_progress_dialog import UpdateProgressDialog
from app.release_info import github_repo
from app.settings import load_settings, save_settings

if TYPE_CHECKING:
    from app.qt.main_window import MainWindow


class MainWindowUpdateMixin:
    """Update check, download, and installer shutdown."""

    def _maybe_check_updates_on_startup(self: MainWindow) -> None:
        settings = load_settings()
        if not settings.get("check_updates_on_startup", True):
            return
        dismissed = str(settings.get("dismissed_update_version", "")).strip()
        self._check_updates(silent=True, skip_version=dismissed)

    def _check_updates_manual(self: MainWindow) -> None:
        self._check_updates(silent=False)

    def _cancel_update_check(self: MainWindow) -> None:
        self._update_check_token = getattr(self, "_update_check_token", 0) + 1
        self._update_check_running = False
        self._stop_update_check_watchdog()

    def _dismiss_download_progress(self: MainWindow) -> None:
        progress = getattr(self, "_download_progress", None)
        self._download_progress = None
        if progress is None:
            return
        progress.hide()
        progress.setVisible(False)
        progress.close()
        progress.deleteLater()

    def _check_updates(self: MainWindow, *, silent: bool, skip_version: str = "") -> None:
        if getattr(self, "_download_runner", None) is not None:
            if not silent:
                alert(self, BRAND_NAME, "Загрузка обновления уже выполняется…")
            return
        if getattr(self, "_update_check_running", False):
            if not silent:
                alert(self, BRAND_NAME, "Проверка обновлений уже выполняется…")
            return

        self._update_check_token = getattr(self, "_update_check_token", 0) + 1
        token = self._update_check_token
        self._update_check_running = True
        if not silent:
            self.status_bar.set_message("Проверка обновлений…", "info")

        self._update_runner = UpdateCheckRunner(self)
        self._update_runner.finished.connect(
            lambda info, error: self._on_update_check_finished(
                info, error, token=token, silent=silent, skip_version=skip_version
            )
        )
        if not silent:
            self._update_check_watchdog = QTimer(self)
            self._update_check_watchdog.setSingleShot(True)
            self._update_check_watchdog.timeout.connect(
                lambda: self._on_update_check_timeout(silent=silent)
            )
            self._update_check_watchdog.start(45_000)
        self._update_runner.start()

    def _stop_update_check_watchdog(self: MainWindow) -> None:
        watchdog = getattr(self, "_update_check_watchdog", None)
        if watchdog is not None:
            watchdog.stop()
            watchdog.deleteLater()
            self._update_check_watchdog = None

    def _on_update_check_timeout(self: MainWindow, *, silent: bool) -> None:
        if silent or not getattr(self, "_update_check_running", False):
            return
        self._cancel_update_check()
        alert(
            self,
            BRAND_NAME,
            "Проверка обновлений заняла слишком много времени. "
            "Проверьте доступ к github.com и повторите попытку.",
        )

    def _on_update_check_finished(
        self: MainWindow,
        info,
        error: str | None,
        *,
        token: int,
        silent: bool,
        skip_version: str,
    ) -> None:
        if token != getattr(self, "_update_check_token", 0):
            return
        self._update_check_running = False
        self._update_runner = None
        self._stop_update_check_watchdog()
        if error:
            if not silent:
                alert(self, BRAND_NAME, error)
            return
        if info is None:
            if not silent:
                alert(self, BRAND_NAME, f"Установлена актуальная версия ({current_version_label()}).")
            return
        if skip_version and info.version == skip_version:
            return
        self._offer_update(info)

    def _offer_update(self: MainWindow, info) -> None:
        asset = info.update or info.portable
        size_mb = round(asset.size / (1024 * 1024), 1) if asset and asset.size else None
        size_line = f"\nРазмер загрузки: ~{size_mb} МБ." if size_mb else ""
        notes = f"\n\n{info.notes}" if info.notes else ""
        text = (
            f"Доступна версия {info.version} (сейчас {current_version_label()})."
            f"{size_line}{notes}"
        )
        box = QMessageBox(self)
        box.setWindowTitle("Обновление")
        box.setText(text)
        box.setIcon(QMessageBox.Icon.Information)
        install = box.addButton("Установить", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Позже", QMessageBox.ButtonRole.RejectRole)
        later = box.addButton("Не напоминать", QMessageBox.ButtonRole.DestructiveRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked == install:
            self._start_update_download(info)
            return
        if clicked == later:
            settings = load_settings()
            settings["dismissed_update_version"] = info.version
            save_settings(settings)

    def _start_update_download(self: MainWindow, info) -> None:
        if getattr(self, "_download_runner", None) is not None:
            alert(self, BRAND_NAME, "Загрузка обновления уже выполняется…")
            return

        progress = UpdateProgressDialog(
            self,
            from_version=current_version_label(),
            to_version=f"v{info.version}",
        )
        progress.cancel_requested.connect(self._cancel_update_download)
        progress.show()

        self._download_progress = progress
        self._download_runner = UpdateDownloadRunner(info)
        self._download_runner.progress.connect(self._on_update_download_progress)
        self._download_runner.phase.connect(self._on_update_download_phase)
        self._download_runner.finished.connect(self._on_update_download_finished)
        self._download_runner.exit_requested.connect(self._exit_for_update)
        self._start_update_download_watchdog()
        self._download_runner.start()

    def _start_update_download_watchdog(self: MainWindow) -> None:
        self._stop_update_download_watchdog()
        self._download_watchdog = QTimer(self)
        self._download_watchdog.setInterval(120_000)
        self._download_watchdog.timeout.connect(self._on_update_download_watchdog)
        self._download_watchdog.start()

    def _stop_update_download_watchdog(self: MainWindow) -> None:
        watchdog = getattr(self, "_download_watchdog", None)
        if watchdog is not None:
            watchdog.stop()
            watchdog.deleteLater()
            self._download_watchdog = None

    def _on_update_download_watchdog(self: MainWindow) -> None:
        progress = getattr(self, "_download_progress", None)
        if progress is not None:
            progress.set_slow_hint(True)

    def _cancel_update_download(self: MainWindow) -> None:
        runner = getattr(self, "_download_runner", None)
        if runner is not None:
            runner.cancel()

    def _on_update_download_progress(self: MainWindow, current: int, total: int) -> None:
        progress = getattr(self, "_download_progress", None)
        if progress is None:
            return
        progress.set_slow_hint(False)
        self._stop_update_download_watchdog()
        self._start_update_download_watchdog()
        progress.set_phase("download", current, total, "")

    def _on_update_download_phase(
        self: MainWindow, phase: str, current: int, total: int, detail: str
    ) -> None:
        progress = getattr(self, "_download_progress", None)
        if progress is None:
            return
        if phase != "download":
            self._stop_update_download_watchdog()
        progress.set_phase(phase, current, total, detail)

    def _on_update_download_finished(self: MainWindow, error: str | None) -> None:
        self._stop_update_download_watchdog()
        runner = self._download_runner
        self._download_runner = None
        if runner is not None:
            try:
                runner.progress.disconnect(self._on_update_download_progress)
            except (RuntimeError, TypeError):
                pass
            try:
                runner.phase.disconnect(self._on_update_download_phase)
            except (RuntimeError, TypeError):
                pass
            try:
                runner.finished.disconnect(self._on_update_download_finished)
            except (RuntimeError, TypeError):
                pass
        self._dismiss_download_progress()
        if error:
            if error == "Обновление отменено":
                alert(self, BRAND_NAME, error)
                return
            self._show_update_download_error(error)

    def _show_update_download_error(self: MainWindow, message: str) -> None:
        from app.paths import app_root
        from app.update.installer import UPDATE_LOG_NAME

        box = QMessageBox(self)
        box.setWindowTitle(BRAND_NAME)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(message)
        log_path = app_root() / UPDATE_LOG_NAME
        open_log = None
        if log_path.is_file():
            open_log = box.addButton("Открыть журнал обновления", QMessageBox.ButtonRole.ActionRole)
        open_page = box.addButton("Открыть страницу загрузки", QMessageBox.ButtonRole.ActionRole)
        box.addButton(BTN_OK, QMessageBox.ButtonRole.AcceptRole)
        box.exec()
        clicked = box.clickedButton()
        if open_log is not None and clicked == open_log:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_path.resolve())))
            return
        if clicked == open_page:
            QDesktopServices.openUrl(QUrl(f"https://github.com/{github_repo()}/releases/latest"))

    def _exit_for_update(self: MainWindow) -> None:
        """Shut down on the GUI thread so the updater can replace files."""
        self._dismiss_download_progress()
        self._cancel_update_check()
        self._browser_watch_timer.stop()
        self._browser_overlay.hide()
        editor_text = self.workspace.prepare_shutdown()
        self._bridge.stop()
        self._controller.shutdown(editor_text=editor_text)
        app = QApplication.instance()
        if app is not None:
            app.quit()
        QTimer.singleShot(2000, lambda: os._exit(0))
