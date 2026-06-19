"""Update check runner posts results from a background thread."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from app.qt.main_window import MainWindow
from app.qt.update_ui import UpdateCheckRunner, UpdateDownloadRunner
from app.update.checker import UpdateAsset, UpdateInfo


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_update_check_runner_emits_from_background_thread(qapp):
    loop = QEventLoop()
    states: list[tuple[object, object]] = []

    runner = UpdateCheckRunner()
    runner.finished.connect(lambda info, error: (states.append((info, error)), loop.quit()))

    with patch("app.qt.update_ui.check_for_updates", return_value=None):
        runner.start()
        QTimer.singleShot(5000, loop.quit)
        loop.exec()

    assert states == [(None, None)]


def test_download_runner_emits_error_on_failure(qapp):
    loop = QEventLoop()
    errors: list[str | None] = []
    asset = UpdateAsset(name="Scenaria-update.zip", url="https://example.com/u.zip", size=1, sha256="")
    info = UpdateInfo(
        version="9.9.9",
        title="Scenaria v9.9.9",
        notes="",
        published_at="2026-01-01T00:00:00Z",
        portable=None,
        update=asset,
    )

    runner = UpdateDownloadRunner(info)
    runner.finished.connect(lambda error: (errors.append(error), loop.quit()))

    with patch("app.qt.update_ui.apply_update", side_effect=RuntimeError("network down")):
        runner.start()
        QTimer.singleShot(5000, loop.quit)
        loop.exec()

    assert errors == ["Ошибка установки обновления: network down"]


def test_dismiss_download_progress_hides_dialog(qapp):
    host = MagicMock()
    progress = QMessageBox()
    progress.show()
    host._download_progress = progress

    MainWindow._dismiss_download_progress(host)

    assert host._download_progress is None
    assert not progress.isVisible()
