"""Recording, playback, and browser session controller."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from app.feature_store import get_root
from app.run_display import compare_run_with_recording
from app.run_status_store import record_run
from app.run_suite import collect_feature_files, format_suite_summary, run_feature_paths
from app.mvc.models.catalog_model import CatalogModel
from app.mvc.models.scenario_model import ScenarioModel
from app.mvc.models.session_model import SessionModel
from app.player import ScenarioPlayer
from app.qt.dialogs import alert, confirm
from app.qt.worker_bridge import WorkerBridge
from app.recorder import ScenarioRecorder
from app.scenario_utils import ScenarioNotFoundError, suggest_scenario_name
from app.steps import apply_coalesced_step
from app.brand import BRAND_NAME


class RecordingController(QObject):
    status = Signal(str, str)  # message, tone
    log = Signal(str, str)  # message, tag
    play_results = Signal(dict, int)  # payload, duration_ms
    switch_tab = Signal(str)
    play_step = Signal(int)
    focus_failed_step = Signal(int)
    save_prompt = Signal(int)  # step count after recording
    picker_done = Signal(str)  # selected selector
    batch_results = Signal(dict, int)  # payload, duration_ms
    browser_raise = Signal(str)  # page title hint for OS-level focus on UI thread

    def __init__(
        self,
        *,
        scenario: ScenarioModel,
        catalog: CatalogModel,
        session: SessionModel,
        recorder: ScenarioRecorder,
        player: ScenarioPlayer,
        scenario_controller,
    ) -> None:
        super().__init__()
        self._scenario = scenario
        self._catalog = catalog
        self._session = session
        self._recorder = recorder
        self._player = player
        self._scenario_controller = scenario_controller
        self._play_log_buffer: list[str] = []
        self._play_started_at = 0.0
        self._picking = False
        self._batch_running = False
        self._batch_stop_requested = False
        self._parent_widget = None
        self._bridge: WorkerBridge | None = None

    def set_parent_widget(self, widget) -> None:
        self._parent_widget = widget

    def attach_bridge(self, bridge: WorkerBridge) -> None:
        self._bridge = bridge
        self._recorder.set_browser_lost_handler(lambda: bridge.emit_event("browser_closed"))
        self._player.set_browser_lost_handler(lambda: bridge.emit_event("player_browser_closed"))
        bridge.on("status", lambda text: self.status.emit(str(text), "normal"))
        bridge.on("step", self._on_step_recorded)
        bridge.on("browser_opened", lambda _: self._on_browser_opened())
        bridge.on("browser_closed", lambda _: self._on_browser_closed())
        bridge.on("player_browser_closed", lambda _: self._on_player_browser_closed())
        bridge.on("recording_started", self._on_recording_started)
        bridge.on("recording_stopped", self._on_recording_stopped)
        bridge.on("pause_toggled", self._on_pause_toggled)
        bridge.on("steps_undone", self._on_steps_undone)
        bridge.on("url_fetched", self._on_url_fetched)
        bridge.on("validation_done", self._on_validation_done)
        bridge.on("error", self._on_error)
        bridge.on("play_log", self._on_play_log)
        bridge.on("play_done", self._on_play_done)
        bridge.on("play_step", self._on_play_step)
        bridge.on("player_browser_started", lambda _: self._on_player_browser_started())
        bridge.on("picker_done", self._on_picker_done)
        bridge.on("batch_done", self._on_batch_done)
        bridge.on("batch_progress", self._on_batch_progress)

    @property
    def is_batch_running(self) -> bool:
        return self._batch_running

    def stop_batch(self) -> None:
        if not self._batch_running:
            return
        self._batch_stop_requested = True
        self.log.emit("Остановка пакета после текущего сценария…", "info")
        self.status.emit("Остановка пакета…", "busy")

    def _emit_session(self) -> None:
        self._session.touch()

    def _set_pending(self, pending: bool, status: str | None = None) -> None:
        self._session.pending = pending
        if pending and status:
            self.status.emit(status, "busy")
        self._emit_session()

    def _recorder_status(self, text: str) -> None:
        self.status.emit(text, "normal")

    def _bridge_ref(self) -> WorkerBridge:
        if self._bridge is None:
            raise RuntimeError("WorkerBridge not attached")
        return self._bridge

    # --- public actions ---

    def sync_browser_state(self) -> None:
        self._sync_browser_state()

    def _sync_browser_state(self) -> None:
        if self._session.browser_open and not self._recorder.browser_open:
            self._on_browser_closed()
        if self._session.player_browser and not self._player.browser_open:
            self._on_player_browser_closed()

    def open_browser(self, url: str) -> None:
        bridge = self._bridge_ref()
        self._sync_browser_state()
        if self._session.pending or self._recorder.is_busy:
            return
        if not self._validate_url(url):
            return
        self._set_pending(True, "Запуск браузера...")
        self.log.emit(f"Открываю браузер: {url}" if url else "Открываю браузер без стартового URL", "info")
        self._recorder.open_browser(
            url,
            self._recorder_status,
            on_complete=lambda: bridge.emit_event("browser_opened"),
            on_error=lambda exc: bridge.emit_event("error", str(exc)),
        )

    def _confirm_replace_steps(self) -> bool:
        if not self._scenario.steps:
            return True
        if self._parent_widget is None:
            return True
        return confirm(
            self._parent_widget,
            BRAND_NAME,
            "Текущие шаги сценария будут заменены записью.\nПродолжить?",
        )

    def quick_record(self, url: str) -> None:
        bridge = self._bridge_ref()
        if self._session.pending or self._recorder.is_busy:
            return
        if not self._validate_url(url):
            return
        if not self._confirm_replace_steps():
            return
        self._scenario.set_steps([])
        self._set_pending(True, "Быстрая запись...")
        self._recorder.quick_record(
            url,
            lambda step: bridge.emit_event("step", step),
            self._recorder_status,
            on_complete=lambda start_url: bridge.emit_event("recording_started", start_url),
            on_error=lambda exc: bridge.emit_event("error", str(exc)),
        )

    def close_browser(self) -> None:
        bridge = self._bridge_ref()
        if self._session.pending or self._recorder.is_busy:
            return
        closed_any = False
        if self._player.browser_open:
            self.close_player_browser()
            closed_any = True
        if not self._recorder.browser_open:
            if not closed_any:
                self.log.emit("Браузер не открыт", "info")
            return
        self._set_pending(True, "Закрытие браузера...")
        self._recorder.close_browser(
            on_complete=lambda: bridge.emit_event("browser_closed"),
            on_error=lambda exc: bridge.emit_event("error", str(exc)),
            on_status=self._recorder_status,
        )

    def focus_browser(self) -> None:
        player_active = (
            self._session.playing
            or self._session.player_browser
            or self._player.browser_open
        )
        if not player_active and not self._recorder.browser_open:
            self.status.emit("Браузер не открыт", "normal")
            return

        player_focused = False
        if player_active:
            player_focused = self._player.focus_browser()

        if self._recorder.browser_open:
            self._recorder.focus_browser(
                on_complete=self._on_browser_focused,
                on_error=lambda exc: self.log.emit(str(exc), "error"),
            )
        elif player_focused:
            self._on_browser_focused("")
        else:
            self.status.emit("Браузер ещё запускается…", "normal")

    def _on_browser_focused(self, title: str) -> None:
        self.browser_raise.emit(title or "")
        self.status.emit("Браузер на переднем плане", "normal")

    def start_recording(self, url: str) -> None:
        bridge = self._bridge_ref()
        if self._session.pending or self._recorder.is_busy:
            return
        if not self._validate_url(url):
            return
        if not self._confirm_replace_steps():
            return
        self._scenario.set_steps([])
        self._set_pending(True, "Подготовка записи...")
        self.log.emit("Старт записи", "info")
        self._recorder.start_recording(
            url,
            lambda step: bridge.emit_event("step", step),
            self._recorder_status,
            on_complete=lambda start_url: bridge.emit_event("recording_started", start_url),
            on_error=lambda exc: bridge.emit_event("error", str(exc)),
        )

    def stop_recording(self) -> None:
        bridge = self._bridge_ref()
        if self._session.pending or not self._session.recording:
            return
        self._set_pending(True, "Остановка записи...")
        self._recorder.stop_recording(
            on_complete=lambda steps: bridge.emit_event("recording_stopped", steps),
            on_error=lambda exc: bridge.emit_event("error", str(exc)),
            on_status=self._recorder_status,
        )

    def toggle_pause(self) -> None:
        bridge = self._bridge_ref()
        if not self._session.recording:
            return
        self._recorder.toggle_pause_recording(
            on_complete=lambda paused: bridge.emit_event("pause_toggled", paused),
            on_error=lambda exc: bridge.emit_event("error", str(exc)),
        )

    def undo_last_step(self) -> None:
        bridge = self._bridge_ref()
        if not self._session.recording:
            return
        self._recorder.undo_last_step(
            on_complete=lambda steps: bridge.emit_event("steps_undone", steps),
            on_error=lambda exc: bridge.emit_event("error", str(exc)),
        )

    def fetch_url_from_tab(self) -> None:
        bridge = self._bridge_ref()
        if not self._recorder.browser_open:
            self.log.emit("Сначала откройте браузер", "error")
            return
        self._recorder.get_active_url(
            on_complete=lambda url: bridge.emit_event("url_fetched", url),
            on_error=lambda exc: bridge.emit_event("error", str(exc)),
        )

    def validate_current(self) -> None:
        bridge = self._bridge_ref()
        try:
            scenario = self._scenario_controller.current_scenario_dict()
        except ScenarioNotFoundError:
            self.log.emit("Нет сценария для проверки", "error")
            return
        if not self._recorder.browser_open:
            self.log.emit("Откройте браузер для проверки селекторов", "error")
            return
        self._set_pending(True, "Проверка сценария...")
        self._recorder.validate_scenario(
            scenario,
            lambda message: bridge.emit_event("play_log", message),
            on_complete=lambda issues: bridge.emit_event("validation_done", issues),
            on_error=lambda exc: bridge.emit_event("error", str(exc)),
            on_status=self._recorder_status,
        )

    @property
    def is_picking(self) -> bool:
        return self._picking

    def pick_selector(self) -> None:
        bridge = self._bridge_ref()
        if self._session.pending or self._recorder.is_busy:
            self.log.emit("Подождите завершения текущей операции", "error")
            return
        if self._session.recording:
            self.log.emit("Остановите запись перед выбором элемента", "error")
            return

        def on_complete(selector: str | None) -> None:
            bridge.emit_event("picker_done", selector or "")

        def on_error(exc: Exception) -> None:
            bridge.emit_event("error", str(exc))

        if self._recorder.browser_open:
            self._start_picking(self._recorder.pick_selector, on_complete, on_error)
            return
        if self._player.browser_open:
            self._start_picking(self._player.pick_selector, on_complete, on_error)
            return
        self.log.emit("Откройте браузер для выбора элемента", "error")

    def _start_picking(self, start, on_complete, on_error) -> None:
        self._picking = True
        self._set_pending(True, "Выбор элемента...")
        self.log.emit("Кликните по элементу в браузере (Esc — отмена)", "info")
        try:
            start(on_complete=on_complete, on_error=on_error)
        except Exception as exc:  # noqa: BLE001
            self._picking = False
            self._set_pending(False)
            self.log.emit(str(exc), "error")

    def cancel_pick_selector(self) -> None:
        if not self._picking:
            return
        if self._recorder.browser_open:
            self._recorder.cancel_pick_selector()
        if self._player.browser_open or self._player.worker_alive:
            self._player.cancel_pick_selector()

    def run_project_suite(self) -> None:
        root = get_root()
        if root is None:
            self.log.emit("Сначала откройте проект с .feature файлами", "error")
            return
        self._start_feature_batch([root], label=f"Запуск всех .feature в {root}")

    def run_selected_features(self, paths: list[Path]) -> None:
        if not paths:
            self.log.emit("Не выбрано ни одного сценария", "error")
            return
        names = ", ".join(path.name for path in paths[:3])
        if len(paths) > 3:
            names += f" и ещё {len(paths) - 3}"
        self._start_feature_batch(paths, label=f"Запуск выбранных: {names}")

    def _start_feature_batch(self, paths: list[Path], *, label: str) -> None:
        if self._session.pending or self._recorder.is_busy or self._batch_running:
            return
        if self._session.recording:
            self.log.emit("Остановите запись перед пакетным запуском", "error")
            return

        files = collect_feature_files(paths)
        if not files:
            self.log.emit("Сценарии .feature не найдены", "error")
            return

        bridge = self._bridge_ref()
        self._batch_running = True
        self._batch_stop_requested = False
        self._play_log_buffer = []
        self._play_started_at = time.time()
        self._session.playing = True
        self._set_pending(True, "Пакетный запуск...")
        self.status.emit("Пакетный запуск сценариев", "playing")
        self.log.emit(label, "info")
        self._emit_session()

        total = len(files)

        def worker() -> None:
            def on_log(message: str) -> None:
                bridge.emit_event("play_log", message)

            progress = {"index": 0}

            def on_case_start(path: Path) -> None:
                progress["index"] += 1
                bridge.emit_event(
                    "batch_progress",
                    {"index": progress["index"], "total": total, "path": str(path)},
                )

            def should_stop() -> bool:
                return self._batch_stop_requested

            try:
                cases = run_feature_paths(
                    paths,
                    headless=True,
                    on_log=on_log,
                    on_case_start=on_case_start,
                    should_stop=should_stop,
                )
            except Exception as exc:  # noqa: BLE001
                bridge.emit_event("error", str(exc))
                bridge.emit_event("batch_done", {"cases": [], "error": str(exc)})
                return
            bridge.emit_event("batch_done", {"cases": cases, "stopped": self._batch_stop_requested})

        threading.Thread(target=worker, daemon=True, name="batch-run").start()

    def _sync_player_browser_state(self) -> None:
        self._session.player_browser = self._player.browser_open

    def _player_worker_active(self) -> bool:
        return self._player.worker_alive

    @property
    def player_worker_active(self) -> bool:
        return self._player.worker_alive

    def play(self) -> None:
        bridge = self._bridge_ref()
        try:
            scenario = self._scenario_controller.current_scenario_dict()
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

        def on_log(message: str) -> None:
            bridge.emit_event("play_log", message)

        def on_done(payload: dict[str, Any]) -> None:
            bridge.emit_event("play_done", payload)

        def on_step(display_index: int, step_index: int, _step: dict[str, Any]) -> None:
            bridge.emit_event(
                "play_step",
                {"display": display_index, "step_index": step_index},
            )

        if self._session.headless:
            self.log.emit("Запуск теста в отдельном headless-браузере", "info")
            self._start_player_play(scenario, on_log, on_done, headless=True)
            return

        if not self._recorder.browser_open:
            self.log.emit("Браузер не открыт — запускаю новый сеанс для теста", "info")
            self._start_player_play(scenario, on_log, on_done, headless=False)
            return

        self.log.emit("Запуск теста в открытом браузере (активная вкладка)", "info")
        self._set_pending(False)
        self._recorder.play_scenario(
            scenario,
            on_log,
            on_complete=on_done,
            on_error=lambda exc: bridge.emit_event("error", str(exc)),
            on_status=self._recorder_status,
            on_step=on_step,
        )

    def _start_player_play(
        self,
        scenario: dict[str, Any],
        on_log,
        on_done,
        *,
        headless: bool,
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
            )
        except Exception as exc:  # noqa: BLE001
            self._session.playing = False
            self._set_pending(False)
            self._emit_session()
            bridge.emit_event("error", str(exc))
            return

        self._set_pending(False)
        self._emit_session()

    def handle_escape(self) -> None:
        if self._picking:
            self.cancel_pick_selector()
            return
        if self._session.recording:
            self.stop_recording()
            return
        if self._session.playing:
            self.stop_playback()

    def stop_playback(self) -> None:
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

    def close_player_browser(self) -> None:
        if not self._player.browser_open:
            return
        self._player.stop()
        self._session.player_browser = False
        self._emit_session()

    def apply_recording_modes(self) -> None:
        self._recorder.set_filter_mode(self._session.filter_recording)
        self._recorder.set_nav_only_mode(self._session.nav_only_recording)

    def on_step_row_selected(self, step: object) -> None:
        if not self._recorder.browser_open:
            return
        on_error = lambda exc: self.log.emit(str(exc), "error")
        if not step or not isinstance(step, dict):
            self._recorder.clear_highlight(on_error=on_error)
            return
        selector = step.get("selector")
        if not selector:
            self._recorder.clear_highlight(on_error=on_error)
            return
        self._recorder.highlight_selector(str(selector), on_error=on_error)

    # --- bridge handlers ---

    def _on_browser_opened(self) -> None:
        self._session.browser_open = True
        self._set_pending(False)
        self.status.emit("Браузер открыт", "success")
        self.log.emit("Браузер готов", "success")
        self._emit_session()

    def _on_player_browser_started(self) -> None:
        self._session.player_browser = True
        self._set_pending(False)
        self.status.emit("Браузер теста запущен", "success")
        self.log.emit("Браузер теста готов", "success")
        self._emit_session()

    def _on_browser_closed(self) -> None:
        self._session.browser_open = False
        self._session.recording = False
        self._session.paused = False
        self._picking = False
        if not self._batch_running:
            self._session.playing = False
        self._set_pending(False)
        self.status.emit("Браузер закрыт", "normal")
        self.log.emit("Браузер закрыт", "info")
        self._emit_session()

    def _on_player_browser_closed(self) -> None:
        self._session.player_browser = False
        self._picking = False
        if not self._batch_running:
            self._session.playing = False
        self._set_pending(False)
        self.status.emit("Браузер теста закрыт", "normal")
        self.log.emit("Браузер теста закрыт", "info")
        self._emit_session()

    def _on_recording_started(self, start_url: str = "") -> None:
        self._session.browser_open = True
        self._session.recording = True
        self._session.paused = False
        self._set_pending(False)
        if start_url and start_url not in {"", "about:blank"}:
            self._scenario.set_start_url(start_url)
            self.log.emit(f"Стартовый URL из вкладки: {start_url}", "info")
        self.switch_tab.emit("editor")
        self.status.emit("Запись активна — выполняйте действия в браузере", "recording")
        self.log.emit("Запись активна", "success")
        self._emit_session()

    def _on_recording_stopped(self, steps: list[dict[str, Any]]) -> None:
        self._scenario.set_steps(steps)
        self._session.recording = False
        self._session.paused = False
        self._session.browser_open = self._recorder.browser_open
        self._set_pending(False)
        self.status.emit(f"Записано шагов: {len(steps)}", "success")
        self.log.emit(f"Запись завершена. Шагов: {len(steps)}", "success")
        if steps:
            last = steps[-1]
            if last.get("action") == "goto" and last.get("url"):
                self.log.emit(f"Финальная страница: {last['url']}", "info")
        if not self._scenario.name.strip():
            suggested = suggest_scenario_name(self._scenario.start_url)
            self._scenario.set_name(suggested)
        if steps:
            self.save_prompt.emit(len(steps))
        self._emit_session()

    def _on_pause_toggled(self, paused: bool) -> None:
        self._session.paused = paused
        self.status.emit("Запись на паузе" if paused else "Запись продолжена", "paused" if paused else "recording")
        self._emit_session()

    def _on_steps_undone(self, steps: list[dict[str, Any]]) -> None:
        self._scenario.set_steps(steps)
        self.log.emit(f"Шагов после отмены: {len(steps)}", "info")

    def _on_url_fetched(self, url: str) -> None:
        self._scenario.set_start_url(url)
        self.log.emit(f"URL из вкладки: {url}", "info")

    def _on_validation_done(self, issues: list[str]) -> None:
        self._set_pending(False)
        if issues:
            self.log.emit(f"Проверка: найдено проблем — {len(issues)}", "error")
            for issue in issues:
                self.log.emit(f"  • {issue}", "error")
            self.status.emit(f"Проблем: {len(issues)}", "error")
        else:
            self.log.emit("Проверка пройдена — селекторы найдены", "success")
            self.status.emit("Сценарий готов к запуску", "success")

    def _on_error(self, message: str) -> None:
        self._picking = False
        self._batch_running = False
        self._recorder.stop_playback()
        self._session.playing = False
        self._set_pending(False)
        if self._player.worker_alive:
            threading.Thread(
                target=self._player.stop,
                daemon=True,
                name="player-stop",
            ).start()
        brief = self._status_brief(str(message))
        self.status.emit(brief, "error")
        self.log.emit(f"Ошибка: {message}", "error")
        self._sync_player_browser_state()
        self._emit_session()

    def _on_play_log(self, message: str) -> None:
        self._play_log_buffer.append(message)
        self.log.emit(message, "info")

    def _on_play_step(self, payload: dict[str, Any]) -> None:
        step_index = int(payload.get("step_index", payload.get("index", -1)))
        if step_index >= 0:
            self.switch_tab.emit("editor")
            self.play_step.emit(step_index)

    def _on_play_done(self, payload: dict[str, Any]) -> None:
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
            if path is not None:
                record_run(path, success=success, message=message)
                self._catalog.refresh_run_statuses()
            results_payload = {
                **payload,
                "duration_ms": duration_ms,
                "log_lines": list(self._play_log_buffer[-40:]),
                "comparison": compare_run_with_recording(self._scenario.steps, payload),
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

    def _on_picker_done(self, selector: str) -> None:
        self._picking = False
        self._set_pending(False)
        if selector:
            self.log.emit(f"Селектор: {selector}", "success")
            self.picker_done.emit(selector)
        else:
            self.log.emit("Выбор элемента отменён", "info")

    def _on_batch_progress(self, payload: dict[str, Any]) -> None:
        index = int(payload.get("index", 0))
        total = int(payload.get("total", 0))
        path = Path(str(payload.get("path", "")))
        label = path.name if path.name else "сценарий"
        self.status.emit(f"Пакет: {index}/{total} — {label}", "playing")

    def _on_batch_done(self, payload: dict[str, Any]) -> None:
        self._batch_running = False
        self._batch_stop_requested = False
        self._session.playing = False
        self._set_pending(False)
        cases = list(payload.get("cases", []))
        duration_ms = int((time.time() - self._play_started_at) * 1000) if self._play_started_at else 0
        failed = sum(1 for case in cases if not case.get("success"))
        summary = format_suite_summary(cases)
        if payload.get("error"):
            self.status.emit(str(payload["error"]), "error")
            self.log.emit(f"Пакетный запуск: {payload['error']}", "error")
        elif failed:
            self.status.emit(f"Пакет: {len(cases) - failed}/{len(cases)} OK", "error")
            self.log.emit(summary, "error")
        elif payload.get("stopped"):
            self.status.emit(f"Пакет остановлен: {len(cases)} сценариев", "info")
            self.log.emit(summary, "info")
        else:
            self.status.emit(f"Пакет: {len(cases)} сценариев OK", "success")
            self.log.emit(summary, "success")

        if cases:
            self._catalog.refresh_run_statuses()

        results_payload = {
            "success": failed == 0 and not payload.get("error"),
            "message": summary,
            "duration_ms": duration_ms,
            "log_lines": list(self._play_log_buffer[-80:]),
            "comparison": summary,
            "suite_cases": cases,
        }
        self.batch_results.emit(results_payload, duration_ms)
        self.switch_tab.emit("results")
        self._emit_session()

    def _on_step_recorded(self, step: dict[str, Any]) -> None:
        steps = list(self._scenario.steps)
        updated, emitted = apply_coalesced_step(steps, step)
        if emitted is None:
            return
        self._scenario.set_steps(updated)
        self._emit_session()

    def _validate_url(self, url: str) -> bool:
        if not url or url.startswith("http"):
            return True
        self.log.emit("Укажите корректный URL (https://...)", "error")
        return False

    @staticmethod
    def _status_brief(message: str) -> str:
        line = (message or "").splitlines()[0].strip()
        if "Call log:" in line:
            line = line.split("Call log:", 1)[0].strip()
        if len(line) > 120:
            line = line[:117] + "..."
        return line or "Ошибка"
