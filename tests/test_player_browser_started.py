"""Detached playback notifies UI when test browser launches."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.mvc.controllers.recording_controller import RecordingController
from app.mvc.models.catalog_model import CatalogModel
from app.mvc.models.scenario_model import ScenarioModel
from app.mvc.models.session_model import SessionModel
from app.player import ScenarioPlayer
from app.recorder import ScenarioRecorder


def test_start_player_play_emits_browser_started() -> None:
    session = SessionModel()
    recorder = MagicMock(spec=ScenarioRecorder)
    recorder.browser_open = False
    recorder.is_busy = False
    player = MagicMock(spec=ScenarioPlayer)
    player.worker_alive = False
    player.browser_open = False
    scenario_controller = MagicMock()
    scenario_controller.current_scenario_dict.return_value = {
        "name": "T",
        "steps": [{"action": "goto", "url": "https://example.com"}],
    }

    controller = RecordingController(
        scenario=ScenarioModel(),
        catalog=CatalogModel(),
        session=session,
        recorder=recorder,
        player=player,
        scenario_controller=scenario_controller,
    )

    bridge = MagicMock()
    events: list[str] = []

    def emit_event(name: str, *args) -> None:
        events.append(name)
        if name == "player_browser_started":
            controller._on_player_browser_started()

    bridge.emit_event.side_effect = emit_event
    controller.attach_bridge(bridge)

    controller.play()

    player.play.assert_called_once()
    assert session.playing is True
    assert session.pending is False
    assert session.player_browser is False

    on_started = player.play.call_args.kwargs["on_started"]
    assert on_started is not None
    on_started()
    assert session.player_browser is True
    assert "player_browser_started" in events
