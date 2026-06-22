"""Results panel widget tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_results_panel_single_run_summary(qapp) -> None:
    from app.qt.widgets.results_panel import ResultsPanel

    panel = ResultsPanel()
    panel.show_results(
        {
            "success": True,
            "duration_ms": 950,
            "runner": "playwright",
            "comparison": "Выполнено: 3 из 3",
            "log_lines": ["line 1"],
        },
        has_failed_step=False,
    )
    assert "Успех" in panel._summary.text()
    assert "Выполнено" in panel._comparison.text()
    assert not panel._comparison.isHidden()


def test_results_panel_suite_cases(qapp) -> None:
    from app.qt.widgets.results_panel import ResultsPanel

    panel = ResultsPanel()
    feature = Path("login.feature")
    panel.show_results(
        {
            "success": False,
            "suite_cases": [
                {"path": feature, "success": True, "message": ""},
                {"path": Path("checkout.feature"), "success": False, "message": "Assert failed"},
            ],
            "log_lines": [],
        },
        has_failed_step=False,
    )
    assert panel._cases_table.rowCount() == 2
    assert "Ошибка" in panel._cases_table.item(1, 1).text()


def test_run_history_dialog_empty(qapp, tmp_path: Path, monkeypatch) -> None:
    from app.qt.widgets import run_history_dialog

    monkeypatch.setattr(run_history_dialog, "get_run_history", lambda _path: [])
    feature = tmp_path / "demo.feature"
    feature.write_text("Функция: x\n", encoding="utf-8")
    dialog = run_history_dialog.RunHistoryDialog(None, feature)
    dialog.show()
    assert not dialog._empty.isHidden()
    assert dialog._table.isHidden()
