"""Stop and pick-toggle behavior while picker is active."""

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
    player.browser_open = True
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


def test_pick_selector_again_cancels_active_pick(controller: RecordingController) -> None:
    controller._picking = True
    controller._recorder.browser_open = True

    controller.pick_selector()

    controller._recorder.cancel_pick_selector.assert_called_once()


def test_stop_recording_cancels_active_pick(controller: RecordingController) -> None:
    controller._picking = True
    controller._session.recording = True
    controller._session.pending = True
    controller._recorder.browser_open = True

    controller.stop_recording()

    controller._recorder.cancel_pick_selector.assert_called_once()
    controller._recorder.stop_recording.assert_not_called()


def test_stop_recording_not_blocked_by_pending_when_not_picking(
    controller: RecordingController,
) -> None:
    controller._session.recording = True
    controller._session.pending = False

    controller.stop_recording()

    controller._recorder.stop_recording.assert_called_once()
