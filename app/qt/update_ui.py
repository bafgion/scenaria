"""Background update check and install for Qt UI."""

from __future__ import annotations

import sys

from PySide6.QtCore import QObject, QThread, Signal

from app.update.checker import UpdateCheckError, UpdateInfo, check_for_updates
from app.update.installer import apply_update
from app.version import app_version


class UpdateCheckWorker(QObject):
    finished = Signal(object, object)  # UpdateInfo | None, error str | None

    def run(self) -> None:
        try:
            info = check_for_updates()
        except UpdateCheckError as exc:
            self.finished.emit(None, str(exc))
            return
        self.finished.emit(info, None)


class UpdateDownloadWorker(QObject):
    progress = Signal(int, int)
    finished = Signal(object)  # error str | None

    def __init__(self, info: UpdateInfo) -> None:
        super().__init__()
        self._info = info

    def run(self) -> None:
        asset = self._info.update or self._info.portable
        if asset is None:
            self.finished.emit("В релизе нет файла обновления")
            return
        try:
            apply_update(asset, on_progress=self.progress.emit)
        except UpdateCheckError as exc:
            self.finished.emit(str(exc))
            return
        self.finished.emit(None)


def updates_supported() -> bool:
    return bool(getattr(sys, "frozen", False))


def current_version_label() -> str:
    return f"v{app_version()}"
