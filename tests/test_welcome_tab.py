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


def test_welcome_tab_does_not_enable_scenario_actions(qapp) -> None:
    from app.gherkin_ru import steps_to_gherkin
    from app.mvc.controllers.app_controller import AppController
    from app.qt.main_window import MainWindow

    steps = [{"action": "goto", "url": "https://example.com"}]
    text = steps_to_gherkin(steps, scenario_name="demo")

    window = MainWindow(AppController())
    window.show()
    window.workspace.open_untitled(initial_text=text)
    qapp.processEvents()
    window.workspace.gherkin_panel.apply_to_model()
    qapp.processEvents()
    assert window._controller.scenario.steps

    window.workspace.ensure_welcome_tab(activate=True)
    qapp.processEvents()
    window._sync_menu_states()

    assert window.workspace.is_editor_tab_active() is False
    assert not window.workspace.quick_toolbar._buttons["play"].isEnabled()
    assert not window.workspace.quick_toolbar._buttons["record"].isEnabled()
    assert not window.workspace.quick_toolbar._buttons["validate"].isEnabled()
    assert window.workspace.editor_action_bar._file_hint.text() == ""
    assert window.workspace.editor_action_bar._next_step.text() == "Откройте сценарий"


def test_toolbar_density_stable_when_switching_to_welcome(qapp) -> None:
    from app.gherkin_ru import steps_to_gherkin
    from app.mvc.controllers.app_controller import AppController
    from app.qt.main_window import MainWindow

    steps = [{"action": "goto", "url": "https://example.com"}]
    text = steps_to_gherkin(steps, scenario_name="demo")

    window = MainWindow(AppController())
    window.resize(1180, 760)
    window.show()
    window.workspace.open_untitled(initial_text=text)
    qapp.processEvents()
    window.workspace.gherkin_panel.apply_to_model()
    qapp.processEvents()
    compact_before = window.workspace.editor_action_bar.toolbar._compact

    window.workspace.ensure_welcome_tab(activate=True)
    qapp.processEvents()
    window._sync_menu_states()

    assert window.workspace.editor_action_bar.toolbar._compact == compact_before
