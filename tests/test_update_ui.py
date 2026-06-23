"""Update check runner posts results from a background thread."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from app.qt.main_window import MainWindow
from app.qt.update_ui import UpdateCheckRunner, UpdateDownloadRunner
from app.qt.widgets.update_progress_dialog import UpdateProgressDialog
from app.update.checker import UpdateAsset, UpdateCheckError, UpdateInfo


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def sync_update_threads():
    """Run update workers synchronously so QSignalSpy does not need QEventLoop."""

    class _SyncThread:
        def __init__(self, target=None, name=None, daemon=None, args=(), kwargs=None):
            self._target = target

        def start(self) -> None:
            if self._target is not None:
                self._target()

    with patch("app.qt.update_ui.threading.Thread", _SyncThread):
        yield


def _update_info() -> UpdateInfo:
    asset = UpdateAsset(name="Scenaria-update.zip", url="https://example.com/u.zip", size=1, sha256="")
    return UpdateInfo(
        version="9.9.9",
        title="Scenaria v9.9.9",
        notes="",
        published_at="2026-01-01T00:00:00Z",
        portable=None,
        update=asset,
    )


def test_update_check_runner_emits_from_background_thread(qapp, sync_update_threads):
    runner = UpdateCheckRunner()
    spy = QSignalSpy(runner.finished)

    with patch("app.qt.update_ui.check_for_updates", return_value=None):
        runner.start()

    assert spy.count() == 1
    assert spy.at(0) == [None, None]


def test_download_runner_emits_error_on_failure(qapp, sync_update_threads):
    runner = UpdateDownloadRunner(_update_info())
    spy = QSignalSpy(runner.finished)

    with patch("app.qt.update_ui.apply_update", side_effect=RuntimeError("network down")):
        runner.start()

    assert spy.count() == 1
    assert spy.at(0) == ["Ошибка установки обновления: network down"]


def test_download_runner_emits_phase_signal(qapp, sync_update_threads):
    runner = UpdateDownloadRunner(_update_info())
    phase_spy = QSignalSpy(runner.phase)
    finished_spy = QSignalSpy(runner.finished)

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

    assert finished_spy.count() == 1
    phases = [tuple(phase_spy.at(i)) for i in range(phase_spy.count())]
    assert ("download", 50, 100, "Scenaria-update.zip") in phases
    assert ("extract", 1, 2, "Scenaria/Scenaria.exe") in phases
    assert ("stage", 2, 2, "Scenaria.exe") in phases


def test_download_runner_emits_exit_requested(qapp, sync_update_threads):
    runner = UpdateDownloadRunner(_update_info())
    exit_spy = QSignalSpy(runner.exit_requested)
    finished_spy = QSignalSpy(runner.finished)

    def fake_apply(_asset, on_progress=None, on_phase=None, on_exit_requested=None, should_cancel=None):
        if on_exit_requested is not None:
            on_exit_requested()

    with patch("app.qt.update_ui.apply_update", side_effect=fake_apply):
        runner.start()

    assert finished_spy.count() == 1
    assert exit_spy.count() == 1


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


def test_download_runner_cancel_emits_message(qapp, sync_update_threads):
    runner = UpdateDownloadRunner(_update_info())
    spy = QSignalSpy(runner.finished)

    def fake_apply(_asset, on_progress=None, on_phase=None, on_exit_requested=None, should_cancel=None):
        if on_progress is not None:
            on_progress(1024, 0)
        if should_cancel is not None and should_cancel():
            raise UpdateCheckError("Обновление отменено")
        raise AssertionError("expected cancel flag before apply completes")

    runner.cancel()
    with patch("app.qt.update_ui.apply_update", side_effect=fake_apply):
        runner.start()

    assert spy.count() == 1
    assert spy.at(0) == ["Обновление отменено"]


def test_dismiss_download_progress_hides_dialog(qapp):
    host = MagicMock()
    progress = UpdateProgressDialog(None, from_version="v0.5.8", to_version="v0.5.9")
    progress.show()
    host._download_progress = progress

    MainWindow._dismiss_download_progress(host)

    assert host._download_progress is None
    assert not progress.isVisible()
