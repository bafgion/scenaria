"""Shared protocol for RecordingController mixins (mypy T10)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from PySide6.QtCore import Signal

from app.mvc.models.catalog_model import CatalogModel
from app.mvc.models.scenario_model import ScenarioModel
from app.mvc.models.session_model import SessionModel
from app.player import ScenarioPlayer
from app.qt.worker_bridge import WorkerBridge
from app.recorder import ScenarioRecorder


class RecordingControllerHost(Protocol):
    """Attribute and method surface used by playback/validate/session mixins."""

    log: Signal
    status: Signal
    play_results: Signal
    switch_tab: Signal
    play_step: Signal
    focus_failed_step: Signal
    batch_results: Signal
    batch_partial: Signal
    progress: Signal
    validation_results: Signal
    save_prompt: Signal
    picker_done: Signal
    browser_raise: Signal

    _scenario: ScenarioModel
    _catalog: CatalogModel
    _session: SessionModel
    _recorder: ScenarioRecorder
    _player: ScenarioPlayer
    _scenario_controller: Any
    _bridge: WorkerBridge | None
    _parent_widget: Any
    _picking: bool
    _batch_running: bool
    _batch_stop_requested: bool
    _batch_runner_id: str
    _last_batch_meta: dict[str, Any]
    _append_base_steps: list[dict[str, Any]] | None
    _play_log_buffer: list[str]
    _play_started_at: float
    _play_scenario_queue: list[dict[str, Any]]
    _play_queue_index: int
    _play_start_step: int
    _play_end_step: int | None

    def _bridge_ref(self) -> WorkerBridge: ...
    def _set_pending(self, pending: bool, status: str | None = None) -> None: ...
    def _emit_session(self) -> None: ...
    def _recorder_status(self, text: str) -> None: ...
    def _status_brief(self, message: str) -> str: ...
    def _sync_player_browser_state(self) -> None: ...
    def _sync_browser_state(self) -> None: ...
    def _start_player_play(self, *args: Any, **kwargs: Any) -> None: ...
    def _save_html_report(self, payload: dict[str, Any], *, duration_ms: int) -> Path | None: ...
    def _validate_url(self, url: str) -> bool: ...
    def _confirm_replace_steps(self) -> bool: ...
    def _begin_append_recording(self, url: str) -> None: ...
    def _on_browser_focused(self, title: str) -> None: ...
    def _on_append_start_error(self, exc: BaseException) -> None: ...
    def _on_continue_prepare_done(self, *args: Any, **kwargs: Any) -> None: ...
    def _start_picking(self, start: Any, on_complete: Any, on_error: Any) -> None: ...
    def cancel_pick_selector(self) -> None: ...
    def stop_recording(self) -> None: ...
    def stop_playback(self) -> None: ...
    def _start_feature_batch(self, *args: Any, **kwargs: Any) -> None: ...
