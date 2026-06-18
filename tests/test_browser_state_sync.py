"""Browser session state sync when the user closes the window manually."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.mvc.controllers.recording_controller import RecordingController
from app.mvc.models.catalog_model import CatalogModel
from app.mvc.models.scenario_model import ScenarioModel
from app.mvc.models.session_model import SessionModel
from app.player import ScenarioPlayer
from app.recorder import ScenarioRecorder


@pytest.fixture
def controller() -> RecordingController:
    recorder = MagicMock(spec=ScenarioRecorder)
    recorder.browser_open = False
    recorder.is_busy = False
    player = MagicMock(spec=ScenarioPlayer)
    player.browser_open = False
    player.worker_alive = False
    ctrl = RecordingController(
        scenario=ScenarioModel(),
        catalog=CatalogModel(),
        session=SessionModel(),
        recorder=recorder,
        player=player,
        scenario_controller=MagicMock(),
    )
    bridge = MagicMock()
    ctrl.attach_bridge(bridge)
    return ctrl


def test_sync_browser_state_clears_recorder_flag(controller: RecordingController) -> None:
    controller._session.browser_open = True
    controller._recorder.browser_open = False

    controller.sync_browser_state()

    assert controller._session.browser_open is False


def test_sync_browser_state_clears_player_flag(controller: RecordingController) -> None:
    controller._session.player_browser = True
    controller._player.browser_open = False

    controller.sync_browser_state()

    assert controller._session.player_browser is False


def test_player_browser_closed_handler_clears_session(controller: RecordingController) -> None:
    controller._session.player_browser = True
    controller._session.playing = True
    controller._picking = True

    controller._on_player_browser_closed()

    assert controller._session.player_browser is False
    assert controller._session.playing is False
    assert controller.is_picking is False
