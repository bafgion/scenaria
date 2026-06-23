"""Browser record/session flow (T3-3)."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any


from app.brand import BRAND_NAME
from app.gherkin_ru import GherkinParseError
from app.qt.dialogs import confirm
from app.scenario_utils import ScenarioNotFoundError, suggest_scenario_name
from app.steps import normalize_steps

if TYPE_CHECKING:
    from app.mvc.controllers.recording_controller import RecordingController


class RecordingSessionMixin:
    """Browser record/session flow (T3-3)."""

    def sync_browser_state(self: RecordingController) -> None:
        self._sync_browser_state()

    def _sync_browser_state(self: RecordingController) -> None:
        if self._session.browser_open and not self._recorder.browser_open:
            self._on_browser_closed()
        if self._session.player_browser and not self._player.browser_open:
            self._on_player_browser_closed()

    def _editor_test_client(self: RecordingController) -> str | None:
        from app.gherkin_context import parse_feature_test_client

        text = self._scenario.source_text or ""
        path = self._scenario.feature_path
        if not text.strip() and path and path.exists():
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                return None
        if not text.strip():
            return None
        try:
            return parse_feature_test_client(text)
        except GherkinParseError as exc:
            self.log.emit(str(exc), "error")
            raise

    def open_browser(self: RecordingController, url: str) -> None:
        bridge = self._bridge_ref()
        self._sync_browser_state()
        if self._session.pending or self._recorder.is_busy:
            return
        if not self._validate_url(url):
            return
        try:
            test_client = self._editor_test_client()
        except GherkinParseError:
            return
        self._set_pending(True, "Запуск браузера...")
        if test_client:
            self.log.emit(f"Открываю браузер с TestClient «{test_client}»", "info")
        else:
            self.log.emit(f"Открываю браузер: {url}" if url else "Открываю браузер (чистый сеанс)", "info")
        self._recorder.open_browser(
            url,
            self._recorder_status,
            on_complete=lambda: bridge.emit_event("browser_opened"),
            on_error=lambda exc: bridge.emit_event("error", str(exc)),
            test_client=test_client,
        )

    def _confirm_replace_steps(self: RecordingController) -> bool:
        if not self._scenario.steps:
            return True
        if self._parent_widget is None:
            return True
        return confirm(
            self._parent_widget,
            BRAND_NAME,
            "Текущие шаги сценария будут заменены записью.\nПродолжить?",
        )

    def quick_record(self: RecordingController, url: str) -> None:
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

    def close_browser(self: RecordingController) -> None:
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

    def focus_browser(self: RecordingController) -> None:
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

    def _on_browser_focused(self: RecordingController, title: str) -> None:
        self.browser_raise.emit(title or "")
        self.status.emit("Браузер на переднем плане", "normal")

    def start_recording(self: RecordingController, url: str) -> None:
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
        try:
            test_client = self._editor_test_client()
        except GherkinParseError:
            return
        self._recorder.start_recording(
            url,
            lambda step: bridge.emit_event("step", step),
            self._recorder_status,
            on_complete=lambda start_url: bridge.emit_event("recording_started", start_url),
            on_error=lambda exc: bridge.emit_event("error", str(exc)),
            test_client=test_client,
        )

    def continue_recording(self: RecordingController, url: str, *, prepare_browser: bool = False) -> None:
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

    def _begin_append_recording(self: RecordingController, url: str) -> None:
        bridge = self._bridge_ref()
        self._set_pending(True, "Подготовка дозаписи...")
        base_count = len(self._append_base_steps or [])
        self.log.emit(f"Дозапись: новые шаги добавятся к {base_count} существующим", "info")
        try:
            test_client = self._editor_test_client()
        except GherkinParseError:
            self._append_base_steps = None
            return
        self._recorder.start_recording(
            url,
            lambda step: bridge.emit_event("step", step),
            self._recorder_status,
            on_complete=lambda start_url: bridge.emit_event("recording_started", start_url),
            on_error=self._on_append_start_error,
            append=True,
            test_client=test_client,
        )

    def _on_continue_prepare_done(self: RecordingController, result: dict[str, Any]) -> None:
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

    def _on_append_start_error(self: RecordingController, exc: Exception) -> None:
        self._append_base_steps = None
        self._bridge_ref().emit_event("error", str(exc))

    def stop_recording(self: RecordingController) -> None:
        bridge = self._bridge_ref()
        if self._picking:
            self.cancel_pick_selector()
            return
        if self._session.pending or not self._session.recording:
            return
        self._set_pending(True, "Остановка записи...")
        self._recorder.stop_recording(
            on_complete=lambda steps: bridge.emit_event("recording_stopped", steps),
            on_error=lambda exc: bridge.emit_event("error", str(exc)),
            on_status=self._recorder_status,
        )

    def toggle_pause(self: RecordingController) -> None:
        bridge = self._bridge_ref()
        if not self._session.recording:
            return
        self._recorder.toggle_pause_recording(
            on_complete=lambda paused: bridge.emit_event("pause_toggled", paused),
            on_error=lambda exc: bridge.emit_event("error", str(exc)),
        )

    def undo_last_step(self: RecordingController) -> None:
        bridge = self._bridge_ref()
        if not self._session.recording:
            return
        self._recorder.undo_last_step(
            on_complete=lambda steps: bridge.emit_event("steps_undone", steps),
            on_error=lambda exc: bridge.emit_event("error", str(exc)),
        )

    def fetch_url_from_tab(self: RecordingController) -> None:
        bridge = self._bridge_ref()
        if not self._recorder.browser_open:
            self.log.emit("Сначала откройте браузер", "error")
            return
        self._recorder.get_active_url(
            on_complete=lambda url: bridge.emit_event("url_fetched", url),
            on_error=lambda exc: bridge.emit_event("error", str(exc)),
        )

    def save_browser_session(self: RecordingController, label: str = "", *, on_saved=None, on_error=None) -> None:
        if not self._recorder.browser_open:
            if on_error:
                on_error(RuntimeError("Сначала откройте браузер"))
            else:
                self.log.emit("Сначала откройте браузер", "error")
            return

        def _complete(path: str) -> None:
            self.log.emit(f"TestClient сохранён: {path}", "success")
            if on_saved:
                on_saved(path)

        def _fail(exc: Exception) -> None:
            if on_error:
                on_error(exc)
            else:
                self.log.emit(f"Не удалось сохранить сессию: {exc}", "error")

        self._recorder.save_browser_session(label=label, on_complete=_complete, on_error=_fail)

    def save_test_client_sync(self: RecordingController, name: str) -> str:

        done = threading.Event()
        holder: dict[str, object] = {}

        def _complete(path: str) -> None:
            holder["path"] = path
            done.set()

        def _fail(exc: Exception) -> None:
            holder["error"] = exc
            done.set()

        self.save_browser_session(name, on_saved=_complete, on_error=_fail)
        if not done.wait(timeout=60):
            raise TimeoutError("Сохранение TestClient не завершилось вовремя")
        if holder.get("error"):
            raise holder["error"]  # type: ignore[misc]
        return str(holder.get("path", ""))

    @property
    def is_picking(self: RecordingController) -> bool:
        return self._picking

    def pick_selector(self: RecordingController) -> None:
        bridge = self._bridge_ref()
        if self._picking:
            self.cancel_pick_selector()
            return
        if self._session.pending or self._recorder.is_busy:
            self.log.emit("Подождите завершения текущей операции", "error")
            return
        if self._session.recording and not self._session.paused:
            self.log.emit("Поставьте запись на паузу, чтобы выбрать элемент", "error")
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

    def _start_picking(self: RecordingController, start, on_complete, on_error) -> None:
        self._picking = True
        self._set_pending(True, "Выбор элемента...")
        self.log.emit("Кликните по элементу в браузере (Esc — отмена)", "info")
        try:
            start(on_complete=on_complete, on_error=on_error)
        except Exception as exc:  # noqa: BLE001
            self._picking = False
            self._set_pending(False)
            self.log.emit(str(exc), "error")

    def cancel_pick_selector(self: RecordingController) -> None:
        if not self._picking:
            return
        if self._recorder.browser_open:
            self._recorder.cancel_pick_selector()
        if self._player.browser_open or self._player.worker_alive:
            self._player.cancel_pick_selector()

    def apply_recording_modes(self: RecordingController) -> None:
        self._recorder.set_filter_mode(self._session.filter_recording)
        self._recorder.set_nav_only_mode(self._session.nav_only_recording)
        self._recorder.set_hover_record_mode(self._session.hover_recording)

    def on_step_row_selected(self: RecordingController, step: object) -> None:
        if not self._recorder.browser_open:
            return

        def on_error(exc: BaseException) -> None:
            self.log.emit(str(exc), "error")

        if not step or not isinstance(step, dict):
            self._recorder.clear_highlight(on_error=on_error)
            return
        selector = step.get("selector")
        if not selector:
            self._recorder.clear_highlight(on_error=on_error)
            return
        self._recorder.highlight_selector(str(selector), on_error=on_error)

    def _on_browser_opened(self: RecordingController) -> None:
        self._session.browser_open = True
        self._set_pending(False)
        self.status.emit("Браузер открыт", "success")
        self.log.emit("Браузер готов", "success")
        self._emit_session()

    def _on_browser_closed(self: RecordingController) -> None:
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

    def _on_recording_started(self: RecordingController, start_url: str = "") -> None:
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

    def _on_recording_stopped(self: RecordingController, steps: list[dict[str, Any]]) -> None:
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

    def _on_pause_toggled(self: RecordingController, paused: bool) -> None:
        self._session.paused = paused
        self.status.emit("Запись на паузе" if paused else "Запись продолжена", "paused" if paused else "recording")
        self._emit_session()

    def _on_steps_undone(self: RecordingController, steps: list[dict[str, Any]]) -> None:
        if self._append_base_steps is not None:
            merged = normalize_steps(list(self._append_base_steps) + list(steps))
            self._scenario.set_steps(merged)
            self.log.emit(f"Шагов после отмены: {len(merged)}", "info")
            return
        self._scenario.set_steps(steps)
        self.log.emit(f"Шагов после отмены: {len(steps)}", "info")

    def _on_url_fetched(self: RecordingController, url: str) -> None:
        self._scenario.set_start_url(url)
        self.log.emit(f"URL из вкладки: {url}", "info")

    def _on_picker_done(self: RecordingController, selector: str) -> None:
        self._picking = False
        self._set_pending(False)
        if selector:
            self.log.emit(f"Селектор: {selector}", "success")
            self.picker_done.emit(selector)
        else:
            self.log.emit("Выбор элемента отменён", "info")

    def _validate_url(self: RecordingController, url: str) -> bool:
        if not url or url.startswith("http"):
            return True
        self.log.emit("Укажите корректный URL (https://...)", "error")
        return False
