"""Update check runner posts results from a background thread."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from app.qt.update_ui import UpdateCheckRunner


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
