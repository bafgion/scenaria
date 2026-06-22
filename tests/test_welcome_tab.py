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
    assert workspace.tab_bar.count() == 1
    assert workspace._tabs[0].is_welcome


def test_close_welcome_reopens_start_tab(qapp) -> None:
    from app.mvc.controllers.app_controller import AppController
    from app.qt.widgets.editor_workspace import EditorWorkspace, _PAGE_WELCOME

    controller = AppController()
    workspace = EditorWorkspace(controller)
    workspace.show()

    workspace.ensure_welcome_tab(activate=True)
    assert workspace._close_tab_at(0, force=False)
    assert workspace.tab_bar.count() == 1
    assert workspace._tabs[0].is_welcome
    assert workspace.stack.currentIndex() == _PAGE_WELCOME


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
    from app.qt.widgets.editor_workspace import EditorWorkspace

    steps = [{"action": "goto", "url": "https://example.com"}]
    text = steps_to_gherkin(steps, scenario_name="demo")

    controller = AppController()
    workspace = EditorWorkspace(controller)
    workspace.show()
    workspace.open_untitled(initial_text=text)
    qapp.processEvents()
    controller.scenario.set_steps(steps)
    qapp.processEvents()
    assert controller.scenario.steps

    workspace.ensure_welcome_tab(activate=True)
    qapp.processEvents()
    workspace.quick_toolbar.sync_states(
        pending=False,
        browser_open=False,
        recording=False,
        playing=False,
        has_steps=False,
        editor_active=False,
    )
    workspace.sync_chrome(
        pending=False,
        browser_open=False,
        recording=False,
        playing=False,
        has_steps=False,
    )

    assert workspace.is_editor_tab_active() is False
    assert not workspace.quick_toolbar._buttons["play"].isEnabled()
    assert not workspace.quick_toolbar._buttons["record"].isEnabled()
    assert not workspace.quick_toolbar._buttons["validate"].isEnabled()
    assert not workspace.editor_action_bar._run_box.isVisible()
    assert not workspace.editor_action_bar._url_edit.isEnabled()


def test_toolbar_density_stable_when_switching_to_welcome(qapp) -> None:
    from app.gherkin_ru import steps_to_gherkin
    from app.mvc.controllers.app_controller import AppController
    from app.qt.widgets.editor_workspace import EditorWorkspace

    steps = [{"action": "goto", "url": "https://example.com"}]
    text = steps_to_gherkin(steps, scenario_name="demo")

    controller = AppController()
    workspace = EditorWorkspace(controller)
    workspace.resize(1180, 760)
    workspace.show()
    workspace.open_untitled(initial_text=text)
    qapp.processEvents()
    controller.scenario.set_steps(steps)
    qapp.processEvents()
    compact_before = workspace.editor_action_bar.toolbar.is_auto_compact()

    workspace.ensure_welcome_tab(activate=True)
    qapp.processEvents()
    workspace.quick_toolbar.sync_states(
        pending=False,
        browser_open=False,
        recording=False,
        playing=False,
        has_steps=False,
        editor_active=False,
    )
    workspace.sync_chrome(
        pending=False,
        browser_open=False,
        recording=False,
        playing=False,
        has_steps=False,
    )

    assert workspace.editor_action_bar.toolbar.is_auto_compact() == compact_before
