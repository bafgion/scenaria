"""Overlay hides when browser session ends after playback."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from app.mvc.controllers.recording_controller import RecordingController
from app.mvc.models.catalog_model import CatalogModel
from app.mvc.models.scenario_model import ScenarioModel
from app.mvc.models.session_model import SessionModel
from app.player import ScenarioPlayer
from app.qt.widgets.browser_overlay import BrowserOverlayPanel
from app.recorder import ScenarioRecorder


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def controller() -> RecordingController:
    recorder = MagicMock(spec=ScenarioRecorder)
    recorder.browser_open = False
    recorder.is_busy = False
    player = MagicMock(spec=ScenarioPlayer)
    player.browser_open = False
    player.worker_alive = True
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


def test_browser_closed_clears_playing_even_if_player_worker_alive(
    controller: RecordingController,
) -> None:
    controller._session.browser_open = True
    controller._session.playing = True

    controller._on_browser_closed()

    assert controller._session.browser_open is False
    assert controller._session.playing is False


def test_overlay_hides_when_no_browser_session(qapp) -> None:
    overlay = BrowserOverlayPanel()
    overlay.show()

    overlay.sync_state(
        visible=False,
        recording=False,
        playing=False,
        paused=False,
        recorder_browser=False,
        player_browser=False,
        picking=False,
    )

    assert not overlay.isVisible()
