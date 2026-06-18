"""Recording controller routes picker to the player browser."""

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
    scenario_controller = MagicMock()
    ctrl = RecordingController(
        scenario=ScenarioModel(),
        catalog=CatalogModel(),
        session=SessionModel(),
        recorder=recorder,
        player=player,
        scenario_controller=scenario_controller,
    )
    bridge = MagicMock()
    ctrl.attach_bridge(bridge)
    return ctrl


def test_pick_selector_uses_player_when_recorder_closed(controller: RecordingController) -> None:
    events: list[tuple[str, object]] = []

    def emit(event: str, payload: object = None) -> None:
        events.append((event, payload))

    controller._bridge.emit_event = emit  # type: ignore[method-assign]

    controller.pick_selector()

    controller._player.pick_selector.assert_called_once()
    assert controller.is_picking is True
    on_complete = controller._player.pick_selector.call_args.kwargs["on_complete"]
    on_complete("button.buy")
    assert ("picker_done", "button.buy") in events


def test_cancel_pick_selector_uses_player_when_worker_alive(controller: RecordingController) -> None:
    controller._player.browser_open = False
    controller._player.worker_alive = True
    controller._picking = True

    controller.cancel_pick_selector()

    controller._player.cancel_pick_selector.assert_called_once()


def test_handle_escape_cancels_picker(controller: RecordingController) -> None:
    controller._picking = True

    controller.handle_escape()

    controller._player.cancel_pick_selector.assert_called_once()


def test_picker_cancel_emits_picker_done(controller: RecordingController) -> None:
    events: list[tuple[str, object]] = []

    def emit(event: str, payload: object = None) -> None:
        events.append((event, payload))
        if event == "picker_done":
            controller._on_picker_done(str(payload))

    controller._bridge.emit_event = emit  # type: ignore[method-assign]

    controller.pick_selector()
    on_complete = controller._player.pick_selector.call_args.kwargs["on_complete"]
    on_complete(None)

    assert controller.is_picking is False
    assert ("picker_done", "") in events
