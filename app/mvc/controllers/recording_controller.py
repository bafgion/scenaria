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
from app.run_suite import collect_feature_files, format_suite_summary
from app.plugins.models import RunMode, RunRequest
from app.plugins.registry import get_registry
from app.mvc.models.catalog_model import CatalogModel
from app.mvc.models.scenario_model import ScenarioModel
from app.mvc.models.session_model import SessionModel
from app.mvc.controllers.playback_coordinator import PlaybackCoordinatorMixin
from app.mvc.controllers.recording_session import RecordingSessionMixin
from app.mvc.controllers.validate_coordinator import ValidateCoordinatorMixin
from app.player import ScenarioPlayer
from app.qt.worker_bridge import WorkerBridge
from app.recorder import ScenarioRecorder
from app.scenario_utils import ScenarioNotFoundError  # noqa: F401 — re-export for tests
from app.steps import apply_coalesced_step

class RecordingController(
    QObject,
    PlaybackCoordinatorMixin,
    ValidateCoordinatorMixin,
    RecordingSessionMixin,
):
    status = Signal(str, str)  # message, tone
    log = Signal(str, str)  # message, tag
    play_results = Signal(dict, int)  # payload, duration_ms
    switch_tab = Signal(str)
    play_step = Signal(int)
    focus_failed_step = Signal(int)
    save_prompt = Signal(int)  # step count after recording
    picker_done = Signal(str)  # selected selector
    batch_results = Signal(dict, int)  # payload, duration_ms
    batch_partial = Signal(dict)  # partial suite cases during batch run
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
        self._play_scenario_queue: list[dict[str, Any]] = []
        self._play_queue_index = 0

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
        bridge.on("play_queue_continue", lambda _: self._on_play_queue_continue())
        bridge.on("play_step", self._on_play_step)
        bridge.on("player_browser_started", lambda _: self._on_player_browser_started())
        bridge.on("picker_done", self._on_picker_done)
        bridge.on("batch_done", self._on_batch_done)
        bridge.on("batch_progress", self._on_batch_progress)
        bridge.on("batch_partial", self._on_batch_partial)
        bridge.on("continue_prepare_done", self._on_continue_prepare_done)

    @property
    def is_batch_running(self) -> bool:
        return self._batch_running

    @property
    def batch_runner_id(self) -> str:
        return self._batch_runner_id

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

        total = len(files)
        bridge = self._bridge_ref()
        self._batch_running = True
        self._batch_stop_requested = False
        self._batch_runner_id = resolved_runner_id
        self._play_log_buffer = []
        self._play_started_at = time.time()
        if resolved_runner_id == "vanessa":
            self._session.vanessa_running = True
            bridge.emit_event(
                "batch_partial",
                {"cases": [], "runner": "vanessa", "total": total, "bootstrap": True},
            )
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
                        "runner": resolved_runner_id,
                    },
                )

            def on_partial_cases(cases) -> None:
                bridge.emit_event(
                    "batch_partial",
                    {
                        "cases": [case.to_dict() for case in cases],
                        "runner": resolved_runner_id,
                        "total": total,
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
                    on_partial_cases=on_partial_cases,
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

    def _on_batch_progress(self, payload: dict[str, Any]) -> None:
        index = int(payload.get("index", 0))
        total = int(payload.get("total", 0))
        label = str(payload.get("path", "") or "").strip() or "сценарий"
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

    def _on_batch_partial(self, payload: dict[str, Any]) -> None:
        cases = list(payload.get("cases") or [])
        if not cases and not payload.get("bootstrap"):
            return
        self.batch_partial.emit(
            {
                "cases": cases,
                "runner": payload.get("runner"),
                "total": int(payload.get("total", 0) or 0),
                "bootstrap": bool(payload.get("bootstrap")),
            }
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

    def _status_brief(self, message: str) -> str:
        line = (message or "").splitlines()[0].strip()
        if "Call log:" in line:
            line = line.split("Call log:", 1)[0].strip()
        if len(line) > 120:
            line = line[:117] + "..."
        return line or "Ошибка"
