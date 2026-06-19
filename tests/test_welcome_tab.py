"""Welcome screen as a closable editor tab."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from app.qt.widgets.editor_workspace import _WELCOME_KEY, _EditorTab


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_welcome_tab_marker() -> None:
    tab = _EditorTab(key=_WELCOME_KEY, path=None, title="Старт")
    assert tab.is_welcome

    regular = _EditorTab(key="file.feature", path=None, title="demo.feature")
    assert not regular.is_welcome


def test_ensure_welcome_tab_is_closable(qapp) -> None:
    from app.mvc.controllers.app_controller import AppController
    from app.qt.widgets.editor_workspace import EditorWorkspace

    controller = AppController()
    workspace = EditorWorkspace(controller)
    workspace.show()

    workspace.ensure_welcome_tab(activate=True)
    assert workspace.tab_bar.count() == 1
    assert workspace.tab_bar.tabText(0) == "Старт"
    assert workspace.tab_bar.tabToolTip(0) == "Стартовая страница"
    assert not workspace.tab_bar.tabIcon(0).isNull()
    assert workspace._tabs[0].is_welcome

    assert workspace._close_tab_at(0, force=False)
    assert workspace.tab_bar.count() == 0
    assert not workspace.has_open_tabs()


def test_close_welcome_shows_empty_workspace(qapp) -> None:
    from app.mvc.controllers.app_controller import AppController
    from app.qt.widgets.editor_workspace import EditorWorkspace, _PAGE_EMPTY

    controller = AppController()
    workspace = EditorWorkspace(controller)
    workspace.show()

    workspace.ensure_welcome_tab(activate=True)
    assert workspace._close_tab_at(0, force=False)
    assert workspace.tab_bar.count() == 0
    assert workspace.stack.currentIndex() == _PAGE_EMPTY


def test_welcome_tab_reopens_without_duplicates(qapp) -> None:
    from app.mvc.controllers.app_controller import AppController
    from app.qt.widgets.editor_workspace import EditorWorkspace

    controller = AppController()
    workspace = EditorWorkspace(controller)
    workspace.show()

    workspace.ensure_welcome_tab(activate=True)
    workspace.ensure_welcome_tab(activate=True)
    assert workspace.tab_bar.count() == 1
