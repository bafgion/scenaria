"""Recording controller must not block the GUI thread when stopping playback."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

from app.mvc.controllers.recording_controller import RecordingController


def _make_controller() -> RecordingController:
    controller = RecordingController(
        scenario=MagicMock(),
        catalog=MagicMock(),
        session=MagicMock(),
        recorder=MagicMock(),
        player=MagicMock(),
        scenario_controller=MagicMock(),
    )
    controller._session.playing = True
    controller._session.pending = True
    controller._player.worker_alive = True

    def slow_stop() -> None:
        time.sleep(0.3)

    controller._player.stop.side_effect = slow_stop
    return controller


def test_stop_playback_does_not_block_calling_thread() -> None:
    controller = _make_controller()
    done = threading.Event()

    def run_stop() -> None:
        controller.stop_playback()
        done.set()

    thread = threading.Thread(target=run_stop)
    thread.start()
    assert done.wait(timeout=0.15), "stop_playback blocked the calling thread"
    thread.join(timeout=2)
    assert controller._session.playing is False
    assert controller._session.pending is False
