"""Update check runner posts results from a background thread."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from app.qt.main_window import MainWindow
from app.qt.update_ui import UpdateCheckRunner, UpdateDownloadRunner
from app.qt.widgets.update_progress_dialog import UpdateProgressDialog
from app.update.checker import UpdateAsset, UpdateInfo

_CI = os.environ.get("GITHUB_ACTIONS") == "true"
_skip_qt_thread_on_ci = pytest.mark.skipif(
    _CI,
    reason="Qt QEventLoop with background threads crashes headless Windows CI",
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@_skip_qt_thread_on_ci
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


@_skip_qt_thread_on_ci
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


@_skip_qt_thread_on_ci
def test_download_runner_emits_phase_signal(qapp):
    loop = QEventLoop()
    phases: list[tuple[str, int, int, str]] = []
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
    runner.phase.connect(lambda phase, current, total, detail: phases.append((phase, current, total, detail)))
    runner.finished.connect(loop.quit)

    def fake_apply(_asset, on_progress=None, on_phase=None, on_exit_requested=None, should_cancel=None):
        if on_progress is not None:
            on_progress(50, 100)
        if on_phase is not None:
            on_phase("download", 50, 100, "Scenaria-update.zip")
            on_phase("extract", 1, 2, "Scenaria/Scenaria.exe")
            on_phase("stage", 2, 2, "Scenaria.exe")
        if on_exit_requested is not None:
            on_exit_requested()

    with patch("app.qt.update_ui.apply_update", side_effect=fake_apply):
        runner.start()
        QTimer.singleShot(5000, loop.quit)
        loop.exec()

    assert ("download", 50, 100, "Scenaria-update.zip") in phases
    assert ("extract", 1, 2, "Scenaria/Scenaria.exe") in phases
    assert ("stage", 2, 2, "Scenaria.exe") in phases


@_skip_qt_thread_on_ci
def test_download_runner_emits_exit_requested(qapp):
    loop = QEventLoop()
    exit_hits: list[int] = []
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
    runner.exit_requested.connect(lambda: (exit_hits.append(1), loop.quit()))
    runner.finished.connect(loop.quit)

    def fake_apply(_asset, on_progress=None, on_phase=None, on_exit_requested=None, should_cancel=None):
        if on_exit_requested is not None:
            on_exit_requested()

    with patch("app.qt.update_ui.apply_update", side_effect=fake_apply):
        runner.start()
        QTimer.singleShot(5000, loop.quit)
        loop.exec()

    assert exit_hits == [1]


def test_update_progress_dialog_updates_bar(qapp):
    dialog = UpdateProgressDialog(None, from_version="v0.5.8", to_version="v0.5.9")
    dialog.set_phase("download", 50, 100, "Scenaria-update.zip")
    assert dialog._bar.value() > 0
    assert "Скачивание" in dialog._phase.text()
    dialog.set_phase("extract", 1, 3, "Scenaria/Scenaria.exe")
    assert "Распаковка" in dialog._phase.text()
    assert dialog._bar.value() > dialog._bar.minimum()
    assert not dialog._cancel_btn.isEnabled()


def test_update_progress_dialog_indeterminate_without_total(qapp):
    dialog = UpdateProgressDialog(None, from_version="v0.5.8", to_version="v0.5.9")
    dialog.set_phase("download", 2 * 1024 * 1024, 0, "Scenaria-update.zip")
    assert dialog._bar.maximum() == 0
    assert "2" in dialog._bar.format()
    assert dialog._cancel_btn.isEnabled()


@_skip_qt_thread_on_ci
def test_download_runner_cancel_emits_message(qapp):
    import time

    from app.update.checker import UpdateCheckError

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

    def fake_apply(_asset, on_progress=None, on_phase=None, on_exit_requested=None, should_cancel=None):
        while should_cancel is not None and not should_cancel():
            if on_progress is not None:
                on_progress(1024, 0)
            time.sleep(0.02)
        raise UpdateCheckError("Обновление отменено")

    with patch("app.qt.update_ui.apply_update", side_effect=fake_apply):
        runner.start()
        QTimer.singleShot(100, runner.cancel)
        QTimer.singleShot(5000, loop.quit)
        loop.exec()

    assert errors == ["Обновление отменено"]


def test_dismiss_download_progress_hides_dialog(qapp):
    host = MagicMock()
    progress = UpdateProgressDialog(None, from_version="v0.5.8", to_version="v0.5.9")
    progress.show()
    host._download_progress = progress

    MainWindow._dismiss_download_progress(host)

    assert host._download_progress is None
    assert not progress.isVisible()
