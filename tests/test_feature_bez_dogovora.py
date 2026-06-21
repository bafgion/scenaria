"""Regression: trimming bez_dogovora.feature must not leave a false syntax error."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from app.gherkin_ru import gherkin_to_steps

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "bez_dogovora.feature"


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _short_text(full: str, *, drop_last: int) -> str:
    lines = full.splitlines()
    return "\n".join(lines[: len(lines) - drop_last]) + "\n"


def test_trim_last_two_lines_parses() -> None:
    full = FIXTURE.read_text(encoding="utf-8")
    short = _short_text(full, drop_last=2)
    steps = gherkin_to_steps(short)
    assert len(steps) == 25
    assert steps[-1]["action"] == "click"


def test_editor_auto_apply_after_trim(qapp) -> None:
    from app.mvc.controllers.app_controller import AppController
    from app.qt.widgets.gherkin_panel import GherkinPanel

    full = FIXTURE.read_text(encoding="utf-8")
    short = _short_text(full, drop_last=2)

    controller = AppController()
    panel = GherkinPanel(controller.scenario, controller.scenario_controller)
    panel.show()

    controller.scenario.load_from_path(FIXTURE)
    panel.sync_from_model(force=True)
    assert not panel.has_parse_error
    assert len(controller.scenario.steps) == 27

    panel.editor.setPlainText(short)
    panel._auto_apply_timer.stop()
    panel._auto_apply_if_valid()

    assert not panel.has_parse_error
    assert not panel.is_unapplied
    assert len(controller.scenario.steps) == 25
    assert panel.apply_to_model()


def test_save_after_trim(tmp_path: Path, qapp) -> None:
    from app.mvc.controllers.app_controller import AppController
    from app.qt.widgets.editor_workspace import EditorWorkspace

    full = FIXTURE.read_text(encoding="utf-8")
    short = _short_text(full, drop_last=2)
    target = tmp_path / "trimmed.feature"
    target.write_text(full, encoding="utf-8")

    controller = AppController()
    workspace = EditorWorkspace(controller)
    workspace.show()
    assert workspace.open_file(target)
    qapp.processEvents()

    workspace.gherkin_panel.editor.setPlainText(short)
    qapp.processEvents()
    workspace.gherkin_panel._auto_apply_timer.stop()
    workspace.gherkin_panel._auto_apply_if_valid()
    qapp.processEvents()

    assert workspace.apply_before_action()
    ok, saved = controller.scenario_controller.save_current_scenario(
        editor_text=workspace.gherkin_panel.get_text(),
        target_path=target,
    )
    assert ok
    assert saved is not None
    assert len(gherkin_to_steps(target.read_text(encoding="utf-8"))) == 25


def test_editor_repairs_missing_quote_on_last_line(qapp) -> None:
    from app.mvc.controllers.app_controller import AppController
    from app.qt.widgets.gherkin_panel import GherkinPanel

    full = FIXTURE.read_text(encoding="utf-8")
    short = _short_text(full, drop_last=2)
    broken = short[:-1]  # drop closing quote on last step line

    controller = AppController()
    panel = GherkinPanel(controller.scenario, controller.scenario_controller)
    panel.show()

    controller.scenario.load_from_path(FIXTURE)
    panel.sync_from_model(force=True)
    panel.editor.setPlainText(broken)
    panel._auto_apply_timer.stop()
    panel._auto_apply_if_valid()
    qapp.processEvents()

    assert not panel.has_parse_error
    assert len(controller.scenario.steps) == 25
    assert panel.get_text().splitlines()[-1].endswith('"')
    assert panel.apply_to_model()


def test_unapplied_tab_restore_does_not_show_parse_error(qapp) -> None:
    from app.mvc.controllers.app_controller import AppController
    from app.qt.widgets.editor_workspace import EditorWorkspace

    full = FIXTURE.read_text(encoding="utf-8")
    short = _short_text(full, drop_last=2)

    controller = AppController()
    workspace = EditorWorkspace(controller)
    workspace.show()
    assert workspace.open_file(FIXTURE)
    qapp.processEvents()

    workspace.gherkin_panel.editor.setPlainText(short)
    workspace.gherkin_panel._auto_apply_timer.stop()
    workspace.gherkin_panel._auto_apply_if_valid()
    qapp.processEvents()
    assert not workspace.gherkin_panel.has_parse_error

    workspace.persist_current_tab()
    workspace.open_untitled()
    qapp.processEvents()
    workspace.tab_bar.setCurrentIndex(0)
    qapp.processEvents()

    assert not workspace.gherkin_panel.has_parse_error
    assert len(controller.scenario.steps) == 25
