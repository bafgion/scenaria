"""Top-level application controller."""

from __future__ import annotations

from app.mvc.controllers.catalog_controller import CatalogController
from app.mvc.controllers.recording_controller import RecordingController
from app.mvc.controllers.scenario_controller import ScenarioController
from app.mvc.models.catalog_model import CatalogModel
from app.mvc.models.scenario_model import ScenarioModel
from app.mvc.models.session_model import SessionModel
from app.player import ScenarioPlayer
from app.recorder import ScenarioRecorder
from app.settings import load_settings


class AppController:
    def __init__(self) -> None:
        self._shutdown_done = False
        self.catalog = CatalogModel()
        self.scenario = ScenarioModel()
        self.session = SessionModel()
        self.catalog_controller: CatalogController | None = None
        self.scenario_controller = ScenarioController(self.scenario, self.catalog)
        self.recorder = ScenarioRecorder()
        self.player = ScenarioPlayer()
        self.recording = RecordingController(
            scenario=self.scenario,
            catalog=self.catalog,
            session=self.session,
            recorder=self.recorder,
            player=self.player,
            scenario_controller=self.scenario_controller,
        )

        settings = load_settings()
        self.session.filter_recording = bool(settings.get("filter_recording"))
        self.session.nav_only_recording = bool(settings.get("nav_only_recording"))
        self.session.headless = bool(settings.get("headless"))
        self.session.hover_recording = bool(settings.get("hover_record_enabled"))

    def attach_catalog_ui(self, controller: CatalogController) -> None:
        self.catalog_controller = controller

    def initialize(self) -> None:
        self.recording.apply_recording_modes()
        self.scenario_controller.initialize()
        if self.catalog_controller is not None:
            self.catalog_controller.initialize()

    def shutdown(self, *, editor_text: str | None = None) -> None:
        if self._shutdown_done:
            return
        self._shutdown_done = True
        self.scenario_controller.on_close(editor_text=editor_text)
        self.recording.stop_playback()
        self.player.shutdown()
        self.recorder.shutdown()
