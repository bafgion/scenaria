"""Recording controller edge cases."""

from __future__ import annotations

from unittest.mock import MagicMock

import app.mvc.controllers.recording_controller as recording_controller
from app.mvc.controllers.recording_controller import RecordingController
from app.mvc.models.catalog_model import CatalogModel
from app.mvc.models.scenario_model import ScenarioModel
from app.mvc.models.session_model import SessionModel
from app.player import ScenarioPlayer
from app.recorder import ScenarioRecorder
from app.scenario_utils import ScenarioNotFoundError


def test_scenario_not_found_error_is_imported() -> None:
    assert recording_controller.ScenarioNotFoundError is ScenarioNotFoundError


def _recording_controller() -> RecordingController:
    recorder = MagicMock(spec=ScenarioRecorder)
    recorder.browser_open = False
    recorder.is_busy = False
    player = MagicMock(spec=ScenarioPlayer)
    player.browser_open = False
    ctrl = RecordingController(
        scenario=ScenarioModel(),
        catalog=CatalogModel(),
        session=SessionModel(),
        recorder=recorder,
        player=player,
        scenario_controller=MagicMock(),
    )
    ctrl.attach_bridge(MagicMock())
    return ctrl


def test_editor_test_client_reads_scenario_model() -> None:
    ctrl = _recording_controller()
    ctrl._scenario.set_source_text(
        'Контекст:\n\tДано я подключаю TestClient "DemoUser"\n'
    )
    assert ctrl._editor_test_client() == "DemoUser"


def test_editor_test_client_empty_without_context() -> None:
    ctrl = _recording_controller()
    ctrl._scenario.set_source_text("Функционал: demo\nСценарий: x\n")
    assert ctrl._editor_test_client() is None


def test_open_browser_handles_gherkin_parse_error() -> None:
    ctrl = _recording_controller()
    ctrl._scenario.set_source_text(
        "Контекст:\n\tДано неизвестный шаг в контексте\n"
    )
    ctrl.open_browser("https://example.com")
    ctrl._recorder.open_browser.assert_not_called()


def test_open_browser_passes_test_client_name() -> None:
    ctrl = _recording_controller()
    ctrl._scenario.set_source_text(
        'Контекст:\n\tДано я подключаю TestClient "DemoUser"\n'
    )
    ctrl.open_browser("https://example.com")
    ctrl._recorder.open_browser.assert_called_once()
    kwargs = ctrl._recorder.open_browser.call_args.kwargs
    assert kwargs.get("test_client") == "DemoUser"
