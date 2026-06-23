"""Step editor selector candidate picker."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_edit_step_dialog_accepts_candidate_selector(qapp) -> None:
    step = {
        "action": "click",
        "selector": "button.old",
        "selectorStrategy": "css",
        "selectorCandidates": [
            {"strategy": "testid", "selector": "button[data-testid=go]"},
            {"strategy": "text", "selector": 'button:has-text("Go")'},
        ],
    }
    dialog = __import__(
        "app.qt.widgets.step_editor_dialog", fromlist=["StepEditorDialog"]
    ).StepEditorDialog(None, step, index=0)
    dialog.show()
    assert dialog._selector_combo is not None
    dialog._selector_combo.setCurrentIndex(2)
    dialog.accept()
    edited = dialog.edited_step(step)
    assert edited is not None
    assert edited["selector"] == 'button:has-text("Go")'
