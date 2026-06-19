"""Auto-apply scenario text when syntax is valid."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from app.gherkin_ru import STEP_INDENT


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_auto_apply_valid_scenario_text(qapp) -> None:
    from app.mvc.controllers.app_controller import AppController
    from app.qt.widgets.gherkin_panel import GherkinPanel

    controller = AppController()
    panel = GherkinPanel(controller.scenario, controller.scenario_controller)
    panel.show()

    text = (
        "Функционал: Пример\n"
        "Сценарий: Тест\n"
        f'{STEP_INDENT}Допустим открыт "https://example.com"\n'
        f"{STEP_INDENT}Когда нажимаю \"button\"\n"
    )
    panel.set_text(text, clean=False)
    assert panel.is_dirty

    qapp.processEvents()
    panel._auto_apply_timer.stop()
    panel._auto_apply_if_valid()

    assert not panel.is_dirty
    assert len(controller.scenario.steps) == 2


def test_auto_apply_keeps_dirty_on_syntax_error(qapp) -> None:
    from app.mvc.controllers.app_controller import AppController
    from app.qt.widgets.gherkin_panel import GherkinPanel

    controller = AppController()
    panel = GherkinPanel(controller.scenario, controller.scenario_controller)
    panel.show()
    panel.set_text("Функционал: broken\nСценарий: x\n    это не шаг\n", clean=False)

    panel._auto_apply_timer.stop()
    panel._auto_apply_if_valid()

    assert panel.is_dirty
    assert controller.scenario.steps == []
