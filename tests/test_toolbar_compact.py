"""Compact toolbar mode (F4-9)."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_simple_mode_hides_secondary_row(qapp) -> None:
    from app.qt.widgets.quick_toolbar import QuickToolBar

    toolbar = QuickToolBar()
    toolbar.show()
    assert toolbar._secondary_wrap.isVisible()

    toolbar.set_simple_mode(True)
    assert toolbar.is_simple_mode()
    assert not toolbar._secondary_wrap.isVisible()
    assert toolbar._buttons["validate"].isVisible() is False

    toolbar.set_simple_mode(False)
    assert toolbar._secondary_wrap.isVisible()


def test_main_window_toolbar_compact_setting(qapp) -> None:
    from app.mvc.controllers.app_controller import AppController
    from app.qt.main_window import MainWindow
    from app.settings import load_settings, save_settings

    settings = load_settings()
    settings["toolbar_compact"] = True
    save_settings(settings)

    window = MainWindow(AppController())
    assert window.workspace.editor_action_bar.is_toolbar_simple_mode()
    assert window._act_toolbar_compact.isChecked()

    settings["toolbar_compact"] = False
    save_settings(settings)
