"""Minimal MainWindow lifecycle without launching Chromium."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_main_window_create_show_close(qapp) -> None:
    from app.mvc.controllers.app_controller import AppController
    from app.qt.main_window import MainWindow

    controller = AppController()
    started = time.perf_counter()

    with (
        patch.object(controller.recording, "open_browser", MagicMock()),
        patch("app.player.ScenarioPlayer", MagicMock()),
        patch("app.recorder.ScenarioRecorder", MagicMock()),
    ):
        window = MainWindow(controller)
        window.show()
        qapp.processEvents()
        assert window.menuBar() is not None
        window.close()
        qapp.processEvents()

    assert time.perf_counter() - started < 5.0
