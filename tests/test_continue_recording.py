"""Continue recording (append mode) behavior."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from app.steps import normalize_steps


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_append_merge_preserves_existing_steps() -> None:
    base = [
        {"action": "goto", "url": "https://example.com"},
        {"action": "click", "selector": "button#a"},
    ]
    new_steps = [{"action": "click", "selector": "button#b"}]
    merged = normalize_steps(list(base) + list(new_steps))
    assert len(merged) == 3
    assert merged[0]["action"] == "goto"
    assert merged[-1]["selector"] == "button#b"


def test_continue_recording_dialog_prepare_flag(qapp) -> None:
    from app.qt.widgets.continue_recording_dialog import ContinueRecordingDialog

    dialog = ContinueRecordingDialog(None, step_count=5)
    dialog.show()
    dialog._prepare.setChecked(True)
    assert dialog.prepare_browser() is True
    dialog._prepare.setChecked(False)
    assert dialog.prepare_browser() is False
    QApplication.processEvents()
