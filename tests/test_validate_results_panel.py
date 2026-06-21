"""Validate results panel widget tests."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_validate_results_panel_shows_rows(qapp) -> None:
    from app.qt.widgets.validate_results_panel import ValidateResultsPanel

    panel = ValidateResultsPanel()
    panel.show_results(
        {
            "issues": ["Шаг 2: элемент не найден → button"],
            "results": [
                {"step_index": 1, "action": "goto", "selector": "https://x.com", "status": "ok", "message": ""},
                {
                    "step_index": 2,
                    "action": "click",
                    "selector": "button",
                    "status": "not_found",
                    "message": "элемент не найден",
                },
            ],
        }
    )
    assert panel._table.rowCount() == 2
    assert "проблем" in panel._summary.text().lower()


def test_validate_results_panel_emits_focus(qapp) -> None:
    from app.qt.widgets.validate_results_panel import ValidateResultsPanel

    panel = ValidateResultsPanel()
    seen: list[int] = []
    panel.step_focus_requested.connect(seen.append)
    panel.show_results(
        {
            "issues": [],
            "results": [
                {"step_index": 3, "action": "click", "selector": "a", "status": "ok", "message": ""},
            ],
        }
    )
    panel._on_double_click(0, 0)
    assert seen == [3]
