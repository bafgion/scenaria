"""Playback flow (T3-1)."""

from __future__ import annotations

import threading
import time
from datetime import UTC
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QTimer

from app.brand import BRAND_NAME
from app.feature_store import get_root
from app.qt.dialogs import alert
from app.qt.worker_bridge import WorkerBridge
from app.run_display import compare_run_with_recording
from app.run_status_store import record_run
from app.run_suite import collect_play_scenarios
from app.scenario_utils import ScenarioNotFoundError

if TYPE_CHECKING:
    from app.mvc.controllers.recording_controller import RecordingController


class PlaybackCoordinatorMixin:
    """Playback flow (T3-1)."""

    def _resolve_play_scenarios(self: RecordingController) -> list[dict[str, Any]]:
        path = self._scenario.feature_path
        text = self._scenario.source_text
        if path is not None or text:
            try:
                scenarios = collect_play_scenarios(path, text=text)
                if scenarios:
                    return scenarios
            except (OSError, ValueError):
                pass
        return [self._scenario_controller.current_scenario_dict()]

    def play(self: RecordingController, *, start_step: int = 0, end_step: int | None = None) -> None:
        bridge = self._bridge_ref()
        try:
            self._play_scenario_queue = self._resolve_play_scenarios()
        except ScenarioNotFoundError:
            self.log.emit("Загрузите сценарий или запишите шаги", "error")
            if self._parent_widget:
                alert(self._parent_widget, BRAND_NAME, "Загрузите сценарий или запишите шаги")
            return
        if self._session.pending or self._recorder.is_busy:
            self.log.emit("Подождите завершения текущей операции", "error")
            return
        if self._player.worker_alive:
            self.log.emit("Предыдущий сеанс теста ещё активен — нажмите Стоп", "error")
            return

        self._play_queue_index = 0
        self._play_start_step = start_step
        self._play_end_step = end_step
        if len(self._play_scenario_queue) > 1:
            self.log.emit(f"Таблица примеров: {len(self._play_scenario_queue)} прогонов", "info")
        self._run_next_queued_play(bridge)

    def _run_next_queued_play(self: RecordingController, bridge: WorkerBridge) -> None:
        if self._play_queue_index >= len(self._play_scenario_queue):
            self._play_scenario_queue = []
            return

        scenario = self._play_scenario_queue[self._play_queue_index]
        start_step = self._play_start_step
        end_step = self._play_end_step

        if self._play_queue_index == 0:
            self._sync_player_browser_state()
            if self._session.player_browser and not self._player.browser_open:
                self._session.player_browser = False
            self._play_log_buffer = []
            self._play_started_at = time.time()
            self._session.playing = True
            self._session.last_failed_step_index = None
            self._set_pending(True, "Воспроизведение...")
            self.status.emit("Воспроизведение сценария", "playing")
            self._emit_session()
        elif len(self._play_scenario_queue) > 1:
            title = str(scenario.get("name", "") or f"пример {self._play_queue_index + 1}")
            self.log.emit(f"Прогон: {title}", "info")

        def on_log(message: str) -> None:
            bridge.emit_event("play_log", message)

        def on_done(payload: dict[str, Any]) -> None:
            if not payload.get("success"):
                self._play_scenario_queue = []
                bridge.emit_event("play_done", payload)
                return
            self._play_queue_index += 1
            if self._play_queue_index < len(self._play_scenario_queue):
                bridge.emit_event("play_queue_continue", None)
                return
            total_examples = len(self._play_scenario_queue)
            if total_examples > 1:
                payload = dict(payload)
                payload["message"] = f"Все {total_examples} примеров выполнены успешно"
            self._play_scenario_queue = []
            bridge.emit_event("play_done", payload)

        def on_step(display_index: int, step_index: int, _step: dict[str, Any]) -> None:
            bridge.emit_event(
                "play_step",
                {"display": display_index, "step_index": step_index},
            )

        if self._session.headless:
            if self._play_queue_index == 0:
                self.log.emit("Запуск теста в отдельном headless-браузере", "info")
            self._start_player_play(
                scenario,
                on_log,
                on_done,
                headless=True,
                start_step=start_step,
                end_step=end_step,
            )
            return

        if not self._recorder.browser_open:
            if self._play_queue_index == 0:
                self.log.emit("Браузер не открыт — запускаю новый сеанс для теста", "info")
            self._start_player_play(
                scenario,
                on_log,
                on_done,
                headless=False,
                start_step=start_step,
                end_step=end_step,
            )
            return

        if self._play_queue_index == 0:
            self.log.emit("Запуск теста в открытом браузере (активная вкладка)", "info")
        self._set_pending(False)
        self._recorder.play_scenario(
            scenario,
            on_log,
            on_complete=on_done,
            on_error=lambda exc: bridge.emit_event("error", str(exc)),
            on_status=self._recorder_status,
            on_step=on_step,
            start_step=start_step,
            end_step=end_step,
        )

    def _sync_player_browser_state(self: RecordingController) -> None:
        self._session.player_browser = self._player.browser_open

    def _player_worker_active(self: RecordingController) -> bool:
        return self._player.worker_alive

    @property
    def player_worker_active(self: RecordingController) -> bool:
        return self._player.worker_alive

    def _start_player_play(
        self,
        scenario: dict[str, Any],
        on_log,
        on_done,
        *,
        headless: bool,
        start_step: int = 0,
        end_step: int | None = None,
    ) -> None:
        bridge = self._bridge_ref()

        def on_started() -> None:
            bridge.emit_event("player_browser_started")

        try:
            self._player.play(
                scenario,
                on_log,
                on_done,
                headless=headless,
                on_started=on_started,
                start_step=start_step,
                end_step=end_step,
                project_root=get_root(),
            )
        except Exception as exc:  # noqa: BLE001
            self._session.playing = False
            self._set_pending(False)
            self._emit_session()
            bridge.emit_event("error", str(exc))
            return

        self._set_pending(False)
        self._emit_session()

    def handle_escape(self: RecordingController) -> None:
        if self._picking:
            self.cancel_pick_selector()
            return
        if self._session.recording:
            self.stop_recording()
            return
        if self._session.playing:
            self.stop_playback()

    def stop_playback(self: RecordingController) -> None:
        if self._picking:
            self.cancel_pick_selector()
        self._recorder.stop_playback()
        self._session.playing = False
        self._set_pending(False)
        self._emit_session()
        if self._player.worker_alive:
            threading.Thread(
                target=self._player.stop,
                daemon=True,
                name="player-stop",
            ).start()
        else:
            self._player.stop()
        self._sync_player_browser_state()
        if not self._player.browser_open:
            self._session.player_browser = False
        self._emit_session()

    def close_player_browser(self: RecordingController) -> None:
        if not self._player.browser_open:
            return
        self._player.stop()
        self._session.player_browser = False
        self._emit_session()

    def _on_player_browser_started(self: RecordingController) -> None:
        self._session.player_browser = True
        self._set_pending(False)
        self.status.emit("Браузер теста запущен", "success")
        self.log.emit("Браузер теста готов", "success")
        self._emit_session()

    def _on_player_browser_closed(self: RecordingController) -> None:
        self._session.player_browser = False
        self._picking = False
        if not self._batch_running:
            self._session.playing = False
        self._set_pending(False)
        self.status.emit("Браузер теста закрыт", "normal")
        self.log.emit("Браузер теста закрыт", "info")
        self._emit_session()

    def _on_play_log(self: RecordingController, message: str) -> None:
        self._play_log_buffer.append(message)
        self.log.emit(message, "info")

    def _on_play_step(self: RecordingController, payload: dict[str, Any]) -> None:
        step_index = int(payload.get("step_index", payload.get("index", -1)))
        if step_index >= 0:
            self.switch_tab.emit("editor")
            self.play_step.emit(step_index)

    def _on_play_queue_continue(self: RecordingController) -> None:
        """Start the next outline example after the player worker thread has exited."""
        if not self._play_scenario_queue or self._play_queue_index >= len(self._play_scenario_queue):
            return
        if self._player.worker_alive:
            if self._player.browser_open:
                self._player.stop()
            QTimer.singleShot(50, self._on_play_queue_continue)
            return
        self._run_next_queued_play(self._bridge_ref())

    def _on_play_done(self: RecordingController, payload: dict[str, Any]) -> None:
        try:
            success = bool(payload.get("success"))
            message = str(payload.get("message", ""))
            duration_ms = int((time.time() - self._play_started_at) * 1000) if self._play_started_at else 0
            failed_index = payload.get("failed_step_index")
            if failed_index is not None:
                self._session.last_failed_step_index = int(failed_index)
                self.focus_failed_step.emit(self._session.last_failed_step_index)
            else:
                self._session.last_failed_step_index = None
            self.status.emit(message if success else self._status_brief(message), "success" if success else "error")
            if success:
                self.log.emit("Тест успешно завершён", "success")
            else:
                self.log.emit(f"Тест завершён с ошибкой: {message}", "error")
            path = self._scenario.feature_path
            html_report_path = self._save_html_report(payload, duration_ms=duration_ms)
            if path is not None:
                failed_step = payload.get("failed_step")
                record_run(
                    path,
                    success=success,
                    message=message,
                    duration_ms=duration_ms,
                    failed_step=int(failed_step) if failed_step is not None else None,
                    report_path=str(html_report_path) if html_report_path else None,
                    runner="playwright",
                )
                self._catalog.refresh_run_statuses()
            results_payload = {
                **payload,
                "duration_ms": duration_ms,
                "feature_path": str(path) if path is not None else None,
                "log_lines": list(self._play_log_buffer[-40:]),
                "comparison": compare_run_with_recording(self._scenario.steps, payload),
                "html_report_path": str(html_report_path) if html_report_path else None,
            }
            self.play_results.emit(results_payload, duration_ms)
            self.switch_tab.emit("results")
        finally:
            self._session.playing = False
            self._sync_player_browser_state()
            self.sync_browser_state()
            if not self._session.browser_session_active():
                self._picking = False
            self._set_pending(False)
            self._emit_session()

    def _save_html_report(self: RecordingController, payload: dict[str, Any], *, duration_ms: int) -> Path | None:
        from datetime import datetime

        from app.html_report import save_play_html_report
        from app.settings import load_settings

        if not load_settings().get("save_html_reports", True):
            return None
        try:
            scenario = self._scenario_controller.current_scenario_dict()
        except ScenarioNotFoundError:
            return None
        started = (
            datetime.fromtimestamp(self._play_started_at, tz=UTC)
            if self._play_started_at
            else None
        )
        return save_play_html_report(
            scenario,
            payload,
            feature_path=self._scenario.feature_path,
            started_at=started,
            duration_ms=duration_ms,
        )
