"""Recording, playback, and browser session controller."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from app.progress_state import ProgressState
from app.feature_store import get_root
from app.project_config import default_runner
from app.run_display import compare_run_with_recording
from app.run_status_store import record_run
from app.run_suite import collect_feature_files, format_suite_summary
from app.plugins.models import RunMode, RunRequest
from app.plugins.registry import get_registry
from app.mvc.models.catalog_model import CatalogModel
from app.mvc.models.scenario_model import ScenarioModel
from app.mvc.models.session_model import SessionModel
from app.player import ScenarioPlayer
from app.qt.dialogs import alert, confirm
from app.qt.worker_bridge import WorkerBridge
from app.recorder import ScenarioRecorder
from app.scenario_utils import ScenarioNotFoundError, suggest_scenario_name
from app.steps import apply_coalesced_step, normalize_steps
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
    progress = Signal(object)  # ProgressState | None
    validation_results = Signal(dict)
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
        self._batch_runner_id = "playwright"
        self._last_batch_meta: dict[str, Any] = {}
        self._parent_widget = None
        self._bridge: WorkerBridge | None = None
        self._append_base_steps: list[dict[str, Any]] | None = None

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
        bridge.on("continue_prepare_done", self._on_continue_prepare_done)

    @property
    def is_batch_running(self) -> bool:
        return self._batch_running

    def stop_batch(self) -> None:
        if not self._batch_running:
            return
        self._batch_stop_requested = True
        self.log.emit("Остановка пакетного прогона…", "info")

    def stop_vanessa(self) -> None:
        if not self._session.vanessa_running:
            return
        self._batch_stop_requested = True
        self.log.emit("Остановка прогона Vanessa…", "info")
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
        self._append_base_steps = None
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

    def continue_recording(self, url: str, *, prepare_browser: bool = False) -> None:
        bridge = self._bridge_ref()
        if self._session.pending or self._recorder.is_busy:
            return
        if not self._scenario.steps:
            self.log.emit("Нет шагов для дозаписи", "error")
            return
        if not self._recorder.browser_open:
            self.log.emit("Откройте браузер для дозаписи", "error")
            return
        if self._session.recording or self._session.playing:
            return
        if not self._validate_url(url):
            return

        self._append_base_steps = list(self._scenario.steps)

        if not prepare_browser:
            self._begin_append_recording(url)
            return

        try:
            scenario = self._scenario_controller.current_scenario_dict()
        except ScenarioNotFoundError:
            self._append_base_steps = None
            self.log.emit("Нет сценария для подготовки", "error")
            return

        end_step = len(self._scenario.steps) - 1
        self._set_pending(True, "Подготовка страницы...")
        self._session.playing = True
        self._emit_session()
        self.log.emit("Прогон сценария до последнего шага перед дозаписью", "info")

        def on_log(message: str) -> None:
            bridge.emit_event("play_log", message)

        def on_done(result: dict[str, Any]) -> None:
            bridge.emit_event("continue_prepare_done", result)

        def on_error(exc: Exception) -> None:
            self._append_base_steps = None
            bridge.emit_event("continue_prepare_done", {"success": False, "message": str(exc)})

        self._recorder.play_scenario(
            scenario,
            on_log,
            on_complete=on_done,
            on_error=on_error,
            end_step=end_step,
        )

    def _begin_append_recording(self, url: str) -> None:
        bridge = self._bridge_ref()
        self._set_pending(True, "Подготовка дозаписи...")
        base_count = len(self._append_base_steps or [])
        self.log.emit(f"Дозапись: новые шаги добавятся к {base_count} существующим", "info")
        self._recorder.start_recording(
            url,
            lambda step: bridge.emit_event("step", step),
            self._recorder_status,
            on_complete=lambda start_url: bridge.emit_event("recording_started", start_url),
            on_error=self._on_append_start_error,
            append=True,
        )

    def _on_continue_prepare_done(self, result: dict[str, Any]) -> None:
        self._session.playing = False
        if result.get("success"):
            self._begin_append_recording(self._scenario.start_url or "")
            return
        self._append_base_steps = None
        self._set_pending(False)
        message = str(result.get("message", "") or "Подготовка не удалась")
        self.log.emit("Подготовка не удалась — дозапись отменена", "error")
        if message and message != "Подготовка не удалась":
            self.log.emit(message, "error")
        self.status.emit("Дозапись отменена", "error")
        self._emit_session()

    def _on_append_start_error(self, exc: Exception) -> None:
        self._append_base_steps = None
        self._bridge_ref().emit_event("error", str(exc))

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

    def save_browser_session(self, label: str = "", *, on_saved=None, on_error=None) -> None:
        if not self._recorder.browser_open:
            if on_error:
                on_error(RuntimeError("Сначала откройте браузер"))
            else:
                self.log.emit("Сначала откройте браузер", "error")
            return

        def _complete(path: str) -> None:
            self.log.emit(f"Сессия сохранена: {path}", "success")
            if on_saved:
                on_saved(path)

        def _fail(exc: Exception) -> None:
            if on_error:
                on_error(exc)
            else:
                self.log.emit(f"Не удалось сохранить сессию: {exc}", "error")

        self._recorder.save_browser_session(label=label, on_complete=_complete, on_error=_fail)

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
            on_complete=lambda payload: bridge.emit_event("validation_done", payload),
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

    def run_project_suite_with_runner(self, runner_id: str) -> None:
        root = get_root()
        if root is None:
            self.log.emit("Сначала откройте проект с .feature файлами", "error")
            return
        self._start_feature_batch(
            [root],
            label=f"Запуск всех .feature в {root} ({runner_id})",
            runner_id=runner_id,
        )

    def run_project_tag(self, tag: str) -> None:
        from app.mvc.models.catalog_model import collect_feature_paths_with_tag

        root = get_root()
        if root is None:
            self.log.emit("Сначала откройте проект с .feature файлами", "error")
            return
        normalized = tag.strip().lstrip("@")
        if not normalized:
            self.log.emit("Укажите тег, например smoke", "error")
            return
        paths = collect_feature_paths_with_tag(root, normalized)
        if not paths:
            self.log.emit(f"Нет сценариев с тегом @{normalized}", "error")
            return
        self._start_feature_batch(paths, label=f"Запуск @{normalized}: {len(paths)} сценариев")

    def run_features_with_runner(
        self,
        paths: list[Path],
        *,
        runner_id: str,
        label: str,
        tags: list[str] | None = None,
        exclude_tags: list[str] | None = None,
        scenario_names: list[str] | None = None,
        runner_options: dict[str, Any] | None = None,
    ) -> None:
        self._start_feature_batch(
            paths,
            label=label,
            runner_id=runner_id,
            tags=tags or [],
            exclude_tags=exclude_tags or [],
            scenario_names=scenario_names or [],
            runner_options=runner_options or {},
        )

    def rerun_vanessa_failed(self) -> None:
        meta = dict(self._last_batch_meta)
        run_dir_raw = meta.get("run_dir")
        if not run_dir_raw or meta.get("runner_id") != "vanessa":
            self.log.emit("Нет данных для перезапуска упавших Vanessa", "error")
            return
        from scenaria_vanessa.rerun_failed import build_rerun_request

        request = build_rerun_request(
            project_root=get_root(),
            paths=[Path(item) for item in meta.get("paths", [])],
            run_dir=Path(str(run_dir_raw)),
            tags=list(meta.get("tags") or []),
            exclude_tags=list(meta.get("exclude_tags") or []),
            runner_options=dict(meta.get("runner_options") or {}),
        )
        if request is None:
            self.log.emit("Упавшие сценарии не найдены в JUnit", "info")
            return
        label = f"Повтор упавших Vanessa ({len(request.scenario_names)})"
        self._start_feature_batch(
            request.paths,
            label=label,
            runner_id="vanessa",
            tags=request.tags,
            exclude_tags=request.exclude_tags,
            scenario_names=request.scenario_names,
            runner_options=request.runner_options,
        )

    def run_selected_features(self, paths: list[Path]) -> None:
        if not paths:
            self.log.emit("Не выбрано ни одного сценария", "error")
            return
        names = ", ".join(path.name for path in paths[:3])
        if len(paths) > 3:
            names += f" и ещё {len(paths) - 3}"
        self._start_feature_batch(paths, label=f"Запуск выбранных: {names}")

    def _start_feature_batch(
        self,
        paths: list[Path],
        *,
        label: str,
        runner_id: str | None = None,
        tags: list[str] | None = None,
        exclude_tags: list[str] | None = None,
        scenario_names: list[str] | None = None,
        runner_options: dict[str, Any] | None = None,
    ) -> None:
        if self._session.pending or self._recorder.is_busy or self._batch_running:
            return
        if self._session.recording:
            self.log.emit("Остановите запись перед пакетным запуском", "error")
            return

        resolved_runner_id = runner_id or default_runner(get_root())
        registry = get_registry()
        registry.reload(project_root=get_root())
        runner = registry.get_runner(resolved_runner_id)
        if runner is None:
            self.log.emit(f"Runner «{resolved_runner_id}» не найден", "error")
            return
        available, reason = runner.is_available()
        if not available:
            self.log.emit(f"{runner.label}: {reason}", "error")
            return

        files = collect_feature_files(paths)
        if not files:
            self.log.emit("Сценарии .feature не найдены", "error")
            return

        bridge = self._bridge_ref()
        self._batch_running = True
        self._batch_stop_requested = False
        self._batch_runner_id = resolved_runner_id
        self._play_log_buffer = []
        self._play_started_at = time.time()
        if resolved_runner_id == "vanessa":
            self._session.vanessa_running = True
        else:
            self._session.playing = True
        self._set_pending(True, "Пакетный запуск...")
        self.status.emit("Пакетный запуск сценариев", "playing")
        self.log.emit(label, "info")
        self._last_batch_meta = {
            "paths": [str(path) for path in paths],
            "tags": list(tags or []),
            "exclude_tags": list(exclude_tags or []),
            "runner_id": resolved_runner_id,
            "runner_options": dict(runner_options or {}),
            "scenario_names": list(scenario_names or []),
        }
        self._emit_session()

        total = len(files)

        def worker() -> None:
            from app.settings import load_settings

            settings = load_settings()

            def on_log(message: str) -> None:
                bridge.emit_event("play_log", message)

            def on_progress(state) -> None:
                bridge.emit_event(
                    "batch_progress",
                    {
                        "index": state.current,
                        "total": state.total,
                        "path": state.label,
                    },
                )

            def should_stop() -> bool:
                return self._batch_stop_requested

            request = RunRequest(
                mode=RunMode.FILES,
                paths=paths,
                project_root=get_root(),
                headless=True,
                browser_engine=settings.get("browser_engine"),
                tags=list(tags or []),
                exclude_tags=list(exclude_tags or []),
                scenario_names=list(scenario_names or []),
                runner_options=dict(runner_options or {}),
            )
            try:
                result = runner.run(
                    request,
                    on_log=on_log,
                    on_progress=on_progress,
                    should_stop=should_stop,
                )
            except Exception as exc:  # noqa: BLE001
                bridge.emit_event("error", str(exc))
                bridge.emit_event("batch_done", {"cases": [], "error": str(exc)})
                return
            bridge.emit_event(
                "batch_done",
                {
                    "cases": result.to_legacy_cases(),
                    "stopped": result.stopped,
                    "error": result.error,
                    "runner": result.runner,
                    "run_dir": str(result.run_dir) if result.run_dir else None,
                    "exit_code": result.exit_code,
                },
            )

        threading.Thread(target=worker, daemon=True, name="batch-run").start()

    def _sync_player_browser_state(self) -> None:
        self._session.player_browser = self._player.browser_open

    def _player_worker_active(self) -> bool:
        return self._player.worker_alive

    @property
    def player_worker_active(self) -> bool:
        return self._player.worker_alive

    def play(self, *, start_step: int = 0, end_step: int | None = None) -> None:
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
        self._recorder.set_hover_record_mode(self._session.hover_recording)

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
        if self._append_base_steps is not None:
            self.status.emit("Дозапись активна — новые шаги добавляются в конец", "recording")
            self.log.emit("Дозапись активна", "success")
        else:
            self.status.emit("Запись активна — выполняйте действия в браузере", "recording")
            self.log.emit("Запись активна", "success")
        self._emit_session()

    def _on_recording_stopped(self, steps: list[dict[str, Any]]) -> None:
        if self._append_base_steps is not None:
            base_count = len(self._append_base_steps)
            steps = normalize_steps(list(self._append_base_steps) + list(steps))
            appended = len(steps) - base_count
            self._append_base_steps = None
            self._scenario.set_steps(steps)
            self._session.recording = False
            self._session.paused = False
            self._session.browser_open = self._recorder.browser_open
            self._set_pending(False)
            self.status.emit(f"Дозаписано шагов: {appended} (всего {len(steps)})", "success")
            self.log.emit(f"Дозапись завершена. Добавлено: {appended}, всего: {len(steps)}", "success")
            if steps and not self._scenario.name.strip():
                self._scenario.set_name(suggest_scenario_name(self._scenario.start_url))
            if appended > 0:
                self.save_prompt.emit(len(steps))
            self._emit_session()
            return
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
        if self._append_base_steps is not None:
            merged = normalize_steps(list(self._append_base_steps) + list(steps))
            self._scenario.set_steps(merged)
            self.log.emit(f"Шагов после отмены: {len(merged)}", "info")
            return
        self._scenario.set_steps(steps)
        self.log.emit(f"Шагов после отмены: {len(steps)}", "info")

    def _on_url_fetched(self, url: str) -> None:
        self._scenario.set_start_url(url)
        self.log.emit(f"URL из вкладки: {url}", "info")

    def _on_validation_done(self, payload: dict[str, Any] | list[str]) -> None:
        if isinstance(payload, list):
            payload = {"issues": payload, "results": []}
        issues = list(payload.get("issues") or [])
        self._set_pending(False)
        if issues:
            self.log.emit(f"Проверка: найдено проблем — {len(issues)}", "error")
            for issue in issues:
                self.log.emit(f"  • {issue}", "error")
            self.status.emit(f"Проблем: {len(issues)}", "error")
        else:
            self.log.emit("Проверка пройдена — селекторы найдены", "success")
            self.status.emit("Сценарий готов к запуску", "success")
        self.validation_results.emit({"issues": issues, "results": list(payload.get("results") or [])})

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

    def _save_html_report(self, payload: dict[str, Any], *, duration_ms: int) -> Path | None:
        from datetime import datetime, timezone

        from app.html_report import save_play_html_report
        from app.settings import load_settings

        if not load_settings().get("save_html_reports", True):
            return None
        try:
            scenario = self._scenario_controller.current_scenario_dict()
        except ScenarioNotFoundError:
            return None
        started = (
            datetime.fromtimestamp(self._play_started_at, tz=timezone.utc)
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
        self.progress.emit(
            ProgressState(
                task_id="batch-run",
                label=label,
                current=index,
                total=total,
                cancellable=True,
            )
        )

    def _on_batch_done(self, payload: dict[str, Any]) -> None:
        self.progress.emit(None)
        self._batch_running = False
        self._batch_stop_requested = False
        self._session.playing = False
        self._session.vanessa_running = False
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

        suite_html_index = None
        try:
            from datetime import datetime, timezone

            from app.html_report import save_batch_html_reports

            started = (
                datetime.fromtimestamp(self._play_started_at, tz=timezone.utc)
                if self._play_started_at
                else None
            )
            suite_html_index = save_batch_html_reports(cases, started_at=started)
        except Exception as exc:  # noqa: BLE001
            self.log.emit(f"HTML-отчёт пакета: {exc}", "error")

        if payload.get("run_dir"):
            self._last_batch_meta["run_dir"] = payload.get("run_dir")

        allure_dir = None
        run_dir_raw = payload.get("run_dir")
        if run_dir_raw and payload.get("runner") == "vanessa":
            try:
                from scenaria_vanessa.report_parsers import allure_dir_from_params, load_merged_params

                merged = load_merged_params(Path(str(run_dir_raw)))
                resolved = allure_dir_from_params(merged) or (Path(str(run_dir_raw)) / "allure")
                if resolved.is_dir():
                    allure_dir = str(resolved)
            except Exception:  # noqa: BLE001
                allure_dir = None

        results_payload = {
            "success": failed == 0 and not payload.get("error"),
            "message": summary,
            "duration_ms": duration_ms,
            "log_lines": list(self._play_log_buffer[-80:]),
            "comparison": summary,
            "suite_cases": cases,
            "suite_html_index": suite_html_index,
            "html_report_path": suite_html_index,
            "runner": payload.get("runner"),
            "run_dir": run_dir_raw,
            "allure_dir": allure_dir,
            "exit_code": payload.get("exit_code"),
            "can_rerun_failed": payload.get("runner") == "vanessa" and bool(run_dir_raw) and failed > 0,
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
