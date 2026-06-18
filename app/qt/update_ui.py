"""Background update check and install for Qt UI."""

from __future__ import annotations

import sys
import threading

from PySide6.QtCore import QObject, Signal

from app.update.checker import UpdateCheckError, UpdateInfo, check_for_updates
from app.update.installer import apply_update
from app.version import app_version


class UpdateCheckRunner(QObject):
    """Runs GitHub update check off the GUI thread."""

    finished = Signal(object, object)  # UpdateInfo | None, error str | None

    def start(self) -> None:
        threading.Thread(target=self._work, name="scenaria-update-check", daemon=True).start()

    def _work(self) -> None:
        try:
            info = check_for_updates()
        except UpdateCheckError as exc:
            self.finished.emit(None, str(exc))
            return
        except Exception as exc:  # noqa: BLE001 — must reach UI in windowed EXE
            self.finished.emit(None, f"Ошибка проверки обновлений: {exc}")
            return
        self.finished.emit(info, None)


class UpdateDownloadRunner(QObject):
    progress = Signal(int, int)
    finished = Signal(object)  # error str | None

    def __init__(self, info: UpdateInfo) -> None:
        super().__init__()
        self._info = info

    def start(self) -> None:
        threading.Thread(target=self._work, name="scenaria-update-download", daemon=True).start()

    def _work(self) -> None:
        asset = self._info.update or self._info.portable
        if asset is None:
            self.finished.emit("В релизе нет файла обновления")
            return
        try:
            apply_update(asset, on_progress=self.progress.emit)
        except UpdateCheckError as exc:
            self.finished.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            self.finished.emit(f"Ошибка установки обновления: {exc}")
            return
        self.finished.emit(None)


# Backwards-compatible names for imports/tests.
UpdateCheckWorker = UpdateCheckRunner
UpdateDownloadWorker = UpdateDownloadRunner


def updates_supported() -> bool:
    return bool(getattr(sys, "frozen", False))


def current_version_label() -> str:
    return f"v{app_version()}"
