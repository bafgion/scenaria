"""B3-7: picker and manual tools while recording is paused."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication

from app.mvc.controllers.recording_controller import RecordingController
from app.mvc.models.catalog_model import CatalogModel
from app.mvc.models.scenario_model import ScenarioModel
from app.mvc.models.session_model import SessionModel
from app.player import ScenarioPlayer
from app.recorder import ScenarioRecorder


@pytest.fixture(scope="session")
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


def test_quick_toolbar_picker_enabled_on_pause(qapp) -> None:
    from app.qt.widgets.quick_toolbar import QuickToolBar

    toolbar = QuickToolBar()
    toolbar.sync_states(
        pending=False,
        browser_open=True,
        recorder_browser_open=True,
        recording=True,
        playing=False,
        paused=True,
        has_steps=True,
        editor_active=True,
    )
    assert toolbar._buttons["picker"].isEnabled()


def test_quick_toolbar_picker_disabled_during_recording(qapp) -> None:
    from app.qt.widgets.quick_toolbar import QuickToolBar

    toolbar = QuickToolBar()
    toolbar.sync_states(
        pending=False,
        browser_open=True,
        recorder_browser_open=True,
        recording=True,
        playing=False,
        paused=False,
        has_steps=True,
        editor_active=True,
    )
    assert not toolbar._buttons["picker"].isEnabled()
    assert "паузу" in toolbar._buttons["picker"].toolTip().lower()


def test_browser_overlay_picker_on_pause(qapp) -> None:
    from app.qt.widgets.browser_overlay import BrowserOverlayPanel

    overlay = BrowserOverlayPanel()
    overlay.sync_state(
        visible=True,
        recording=True,
        playing=False,
        paused=True,
        recorder_browser=True,
    )
    assert overlay._btn_picker.isEnabled()
    assert "элемент" in overlay._title.text().lower()


def test_recorder_skips_browser_steps_on_pause() -> None:
    import queue

    from app.recorder import ScenarioRecorder

    recorder = ScenarioRecorder.__new__(ScenarioRecorder)
    recorder._playing = False
    recorder._paused = True
    recorder._step_inbox = queue.Queue()
    recorder._enqueue_browser_step({"action": "click", "selector": "#x"})
    assert recorder._step_inbox.empty()


def test_recorder_pick_selector_allowed_on_pause() -> None:
    import queue
    from unittest.mock import MagicMock, patch

    from app.recorder import ScenarioRecorder

    recorder = ScenarioRecorder.__new__(ScenarioRecorder)
    recorder._recording = True
    recorder._paused = True
    recorder._playing = False
    recorder._pick_cancel_requested = False
    recorder._browser = MagicMock()
    recorder._browser.is_connected.return_value = True
    recorder._picker_result = queue.Queue()
    recorder._commands = queue.Queue()
    recorder._emit_status = MagicMock()

    page = MagicMock()
    with patch.object(recorder, "_get_active_page", return_value=page):
        with patch.object(recorder, "_attach_picker_bindings"):
            with patch.object(recorder, "_drain_picker_result"):
                with patch.object(recorder, "_uninstall_picker"):
                    with patch.object(recorder, "_pump_playwright"):
                        recorder._picker_result.put("button")
                        selector = recorder._handle_pick_selector()
    assert selector == "button"


def test_recorder_pick_selector_blocked_while_recording() -> None:
    from app.recorder import ScenarioRecorder

    recorder = ScenarioRecorder.__new__(ScenarioRecorder)
    recorder._recording = True
    recorder._paused = False
    with pytest.raises(RuntimeError, match="запись"):
        recorder._handle_pick_selector()


def test_recording_controller_pick_on_pause(controller: RecordingController) -> None:
    controller._session.recording = True
    controller._session.paused = True
    controller._recorder.browser_open = True

    controller.pick_selector()

    controller._recorder.pick_selector.assert_called_once()


def test_recording_controller_pick_blocked_while_recording(controller: RecordingController) -> None:
    controller._session.recording = True
    controller._session.paused = False
    controller._recorder.browser_open = True
    events: list[tuple[str, str]] = []
    controller.log.connect(lambda msg, level: events.append((msg, level)))

    controller.pick_selector()

    assert events
    assert "паузу" in events[0][0].lower()
    controller._recorder.pick_selector.assert_not_called()
