"""Manage browser session: browse, record, and replay user actions."""

from __future__ import annotations

import os
import queue
import threading
import time
from enum import Enum, auto
from typing import Any, Callable

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from app.browser_config import browser_context_options, launch_browser, load_browser_engine
from app.browser_focus import focus_browser_context_with_title
from app.http_auth import auth_key, resolve_http_credentials
from app.paths import configure_playwright_browsers
from app.settings import load_settings
from app.playwright_lifecycle import release_playwright_session
from app.picker_script import (
    install_picker_in_all_frames,
    uninstall_picker_from_all_frames,
)
from app.player import PlayResult, highlight_selector, remove_highlight, reset_highlight_cleanup_state, run_scenario_on_page, setup_highlight_cleanup
from app.recorder_script import RECORDER_INIT_SCRIPT, RECORDER_INSTALLED_CHECK
from app.selector_build import apply_smart_selector_to_step
from app.steps import NAV_TIMEOUT_MS, NAV_WAIT_UNTIL, apply_coalesced_step, normalize_steps

BrowserCallback = Callable[[], None]
ErrorCallback = Callable[[Exception], None]
StepsCallback = Callable[[list[dict]], None]
PlayDoneCallback = Callable[[PlayResult], None]
StringCallback = Callable[[str], None]
PickerCallback = Callable[[str | None], None]
IssuesCallback = Callable[[list[str]], None]
UndoCallback = Callable[[list[dict]], None]


class _Command(Enum):
    PREWARM = auto()
    OPEN = auto()
    START_RECORDING = auto()
    STOP_RECORDING = auto()
    PAUSE_TOGGLE = auto()
    UNDO_STEP = auto()
    QUICK_RECORD = auto()
    PLAY = auto()
    VALIDATE = auto()
    GET_URL = auto()
    FOCUS_BROWSER = auto()
    HIGHLIGHT = auto()
    CLEAR_HIGHLIGHT = auto()
    SET_FILTER = auto()
    SET_NAV_ONLY = auto()
    SET_HOVER_RECORD = auto()
    CLOSE = auto()
    BROWSER_SCRIPT = auto()
    PICK_SELECTOR = auto()
    PICK_SELECTOR_CANCEL = auto()
    SAVE_BROWSER_SESSION = auto()
    SHUTDOWN = auto()


class ScenarioRecorder:
    def __init__(self) -> None:
        self._commands: queue.Queue[
            tuple[_Command, dict, object | None, ErrorCallback | None]
        ] = queue.Queue()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True, name="recorder-worker")
        self._worker.start()

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._recording = False
        self._paused = False
        self._filter_mode = False
        self._nav_only_mode = False
        self._hover_record_mode = False
        self._append_mode = False
        self._busy = False
        self._steps: list[dict] = []
        self._on_step: Callable[[dict], None] | None = None
        self._on_status: Callable[[str], None] | None = None
        self._last_goto = ""
        self._context_binding_attached = False
        self._hooked_page_ids: set[int] = set()
        self._browser_open = False
        self._step_inbox: queue.Queue[dict] = queue.Queue()
        self._playing = False
        self._stop_playback = threading.Event()
        self._on_browser_lost: Callable[[], None] | None = None
        self._watchers_attached = False
        self._picker_binding_attached = False
        self._picker_result: queue.Queue[str | None] = queue.Queue()
        self._pick_cancel_requested = False
        self._shutdown_requested = False
        self._session_releasing = False
        self._context_auth_key: tuple[str, str] | None = None
        self._context_test_client: str | None = None
        self._browser_engine: str | None = None

        if os.environ.get("SCENARIA_SKIP_RECORDER_PREWARM") != "1":
            self._enqueue(_Command.PREWARM, {})

    def set_browser_lost_handler(self, handler: Callable[[], None] | None) -> None:
        self._on_browser_lost = handler

    @property
    def browser_open(self) -> bool:
        if not self._browser_open:
            return False
        browser = self._browser
        if browser is None or not browser.is_connected():
            return False
        context = self._context
        if context is not None:
            return any(not page.is_closed() for page in context.pages)
        page = self._page
        return page is not None and not page.is_closed()

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def is_busy(self) -> bool:
        return self._busy

    def open_browser(
        self,
        start_url: str,
        on_status: Callable[[str], None],
        on_complete: BrowserCallback | None = None,
        on_error: ErrorCallback | None = None,
        *,
        test_client: str | None = None,
    ) -> None:
        self._on_status = on_status
        self._enqueue(
            _Command.OPEN,
            {"start_url": start_url, "test_client": test_client},
            on_complete,
            on_error,
        )

    def quick_record(
        self,
        start_url: str,
        on_step: Callable[[dict], None],
        on_status: Callable[[str], None],
        on_complete: BrowserCallback | None = None,
        on_error: ErrorCallback | None = None,
    ) -> None:
        self._steps = []
        self._on_step = on_step
        self._on_status = on_status
        self._last_goto = ""
        self._enqueue(_Command.QUICK_RECORD, {"start_url": start_url}, on_complete, on_error)

    def start_recording(
        self,
        start_url: str,
        on_step: Callable[[dict], None],
        on_status: Callable[[str], None],
        on_complete: BrowserCallback | None = None,
        on_error: ErrorCallback | None = None,
        *,
        append: bool = False,
        test_client: str | None = None,
    ) -> None:
        self._append_mode = append
        self._steps = []
        self._on_step = on_step
        self._on_status = on_status
        self._last_goto = ""
        self._enqueue(
            _Command.START_RECORDING,
            {"start_url": start_url, "append": append, "test_client": test_client},
            on_complete,
            on_error,
        )

    def stop_recording(
        self,
        on_complete: StepsCallback | None = None,
        on_error: ErrorCallback | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> None:
        if on_status:
            self._on_status = on_status
        self._enqueue(_Command.STOP_RECORDING, {}, on_complete, on_error)

    def toggle_pause_recording(
        self,
        on_complete: Callable[[bool], None] | None = None,
        on_error: ErrorCallback | None = None,
    ) -> None:
        self._enqueue(_Command.PAUSE_TOGGLE, {}, on_complete, on_error)

    def undo_last_step(
        self,
        on_complete: UndoCallback | None = None,
        on_error: ErrorCallback | None = None,
    ) -> None:
        self._enqueue(_Command.UNDO_STEP, {}, on_complete, on_error)

    def get_active_url(
        self,
        on_complete: StringCallback | None = None,
        on_error: ErrorCallback | None = None,
    ) -> None:
        self._enqueue(_Command.GET_URL, {}, on_complete, on_error)

    def focus_browser(
        self,
        on_complete: Callable[[bool], None] | None = None,
        on_error: ErrorCallback | None = None,
    ) -> None:
        self._enqueue(_Command.FOCUS_BROWSER, {}, on_complete, on_error)

    def highlight_selector(
        self,
        selector: str,
        on_error: ErrorCallback | None = None,
    ) -> None:
        self._enqueue(_Command.HIGHLIGHT, {"selector": selector}, None, on_error)

    def clear_highlight(self, on_error: ErrorCallback | None = None) -> None:
        self._enqueue(_Command.CLEAR_HIGHLIGHT, {}, None, on_error)

    def set_filter_mode(self, enabled: bool) -> None:
        self._filter_mode = enabled
        self._enqueue(_Command.SET_FILTER, {"enabled": enabled}, None, None)

    def set_nav_only_mode(self, enabled: bool) -> None:
        self._nav_only_mode = enabled
        self._enqueue(_Command.SET_NAV_ONLY, {"enabled": enabled}, None, None)

    def set_hover_record_mode(self, enabled: bool) -> None:
        self._hover_record_mode = enabled
        self._enqueue(_Command.SET_HOVER_RECORD, {"enabled": enabled}, None, None)

    def validate_scenario(
        self,
        scenario: dict,
        on_log: Callable[[str], None],
        on_complete: IssuesCallback | None = None,
        on_error: ErrorCallback | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> None:
        if on_status:
            self._on_status = on_status
        self._enqueue(
            _Command.VALIDATE,
            {"scenario": scenario, "on_log": on_log},
            on_complete,
            on_error,
        )

    def close_browser(
        self,
        on_complete: BrowserCallback | None = None,
        on_error: ErrorCallback | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> None:
        if on_status:
            self._on_status = on_status
        self._enqueue(_Command.CLOSE, {}, on_complete, on_error)

    def play_scenario(
        self,
        scenario: dict,
        on_log: Callable[[str], None],
        on_complete: PlayDoneCallback | None = None,
        on_error: ErrorCallback | None = None,
        on_status: Callable[[str], None] | None = None,
        on_step: Callable[[int, dict], None] | None = None,
        *,
        start_step: int = 0,
        end_step: int | None = None,
    ) -> None:
        if on_status:
            self._on_status = on_status
        self._enqueue(
            _Command.PLAY,
            {
                "scenario": scenario,
                "on_log": on_log,
                "on_step": on_step,
                "start_step": start_step,
                "end_step": end_step,
            },
            on_complete,
            on_error,
        )

    def stop_playback(self) -> None:
        self._stop_playback.set()

    def pick_selector(
        self,
        on_complete: PickerCallback | None = None,
        on_error: ErrorCallback | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> None:
        if on_status:
            self._on_status = on_status
        self._enqueue(_Command.PICK_SELECTOR, {}, on_complete, on_error)

    def cancel_pick_selector(self) -> None:
        self._enqueue(_Command.PICK_SELECTOR_CANCEL, {}, None, None)

    def save_browser_session(
        self,
        *,
        label: str = "",
        on_complete: Callable[[str], None] | None = None,
        on_error: ErrorCallback | None = None,
    ) -> None:
        self._enqueue(_Command.SAVE_BROWSER_SESSION, {"label": label}, on_complete, on_error)

    def shutdown(self) -> None:
        if self._shutdown_requested:
            return
        self._shutdown_requested = True
        self._commands.put((_Command.SHUTDOWN, {}, None, None))
        self._worker.join(timeout=30)

    def _enqueue(
        self,
        command: _Command,
        payload: dict,
        on_complete: object | None = None,
        on_error: ErrorCallback | None = None,
    ) -> None:
        self._commands.put((command, payload, on_complete, on_error))

    def _emit_status(self, text: str) -> None:
        if self._on_status:
            self._on_status(text)

    def _append_step(self, step: dict) -> None:
        if not self._recording or self._paused:
            return
        if step.get("action") == "goto":
            url = step.get("url", "")
            if url and url == self._last_goto:
                return
            self._last_goto = url

        incoming = dict(step)
        incoming = apply_smart_selector_to_step(
            incoming,
            load_settings().get("selector_priority"),
        )
        strategy = incoming.get("selectorStrategy")
        if strategy and incoming.get("selector"):
            self._emit_status(f"Селектор ({strategy}): {incoming['selector'][:100]}")
        if incoming.get("action") == "click" and incoming.get("hoverSelector"):
            hover_step = {
                "action": "hover",
                "selector": incoming["hoverSelector"],
                "text": incoming.get("hoverText", ""),
            }
            if not (
                self._steps
                and self._steps[-1].get("action") == "hover"
                and self._steps[-1].get("selector") == hover_step["selector"]
            ):
                self._push_step(hover_step)

        self._push_step(incoming)

    def _push_step(self, step: dict) -> None:
        step = self._coalesce_step(step)
        if step is None:
            return
        self._steps.append(step)
        if self._on_step:
            self._on_step(step)

    def _coalesce_step(self, step: dict) -> dict | None:
        if not self._steps:
            return step
        updated, emitted = apply_coalesced_step(self._steps, step)
        if emitted is None:
            return None
        if len(updated) == len(self._steps):
            self._steps = updated
            if self._on_step:
                self._on_step(emitted)
            return None
        return emitted

    def _enqueue_browser_step(self, step: dict) -> None:
        if self._playing or self._paused:
            return
        self._step_inbox.put(step)

    def _drain_step_inbox(self) -> None:
        while True:
            try:
                step = self._step_inbox.get_nowait()
            except queue.Empty:
                break
            self._append_step(step)

    def _pump_playwright(self) -> None:
        self._poll_browser_lost()
        page = self._page
        if page is None:
            time.sleep(0.025)
            return
        try:
            if page.is_closed():
                self._poll_browser_lost()
                time.sleep(0.025)
                return
            page.wait_for_timeout(25)
        except Exception:
            self._poll_browser_lost()
            time.sleep(0.025)

    def _poll_browser_lost(self) -> None:
        if self._browser is None and not self._browser_open:
            return
        lost = False
        try:
            if self._browser is not None and not self._browser.is_connected():
                lost = True
            elif self._context is not None:
                alive_pages = [p for p in self._context.pages if not p.is_closed()]
                if self._browser_open and not alive_pages:
                    lost = True
            elif self._page is not None and self._page.is_closed() and self._browser_open:
                lost = True
        except Exception:
            lost = True
        if lost:
            self._handle_browser_disconnected()

    def _attach_session_watchers(self) -> None:
        if self._watchers_attached:
            return
        if self._browser is not None:
            self._browser.on("disconnected", lambda _: self._handle_browser_disconnected())
        if self._context is not None:
            self._context.on("close", lambda _: self._handle_browser_disconnected())
            self._context.on("page", self._watch_page_close)
        self._watch_page_close(self._page)
        self._watchers_attached = True

    def _watch_page_close(self, page: Page | None) -> None:
        if page is None:
            return

        def on_close() -> None:
            self._poll_browser_lost()

        try:
            page.on("close", on_close)
        except Exception:
            pass

    def _worker_loop(self) -> None:
        while True:
            try:
                command, payload, on_complete, on_error = self._commands.get(timeout=0.05)
            except queue.Empty:
                self._pump_playwright()
                self._drain_step_inbox()
                continue

            if command == _Command.SHUTDOWN:
                self._close_session()
                return

            light_commands = {
                _Command.STOP_RECORDING,
                _Command.PAUSE_TOGGLE,
                _Command.UNDO_STEP,
                _Command.GET_URL,
                _Command.FOCUS_BROWSER,
                _Command.HIGHLIGHT,
                _Command.SET_FILTER,
                _Command.SET_NAV_ONLY,
                _Command.PICK_SELECTOR_CANCEL,
                _Command.CLOSE,
                _Command.SAVE_BROWSER_SESSION,
            }
            if command != _Command.PREWARM and self._busy and command not in light_commands:
                self._notify_error(on_error, RuntimeError("Подождите завершения предыдущей операции"))
                continue

            self._busy = command not in light_commands | {_Command.PREWARM}
            try:
                result = self._dispatch_command(command, payload)
                self._drain_step_inbox()
                self._notify_complete(on_complete, result, command)
            except Exception as exc:  # noqa: BLE001
                self._notify_error(on_error, exc)
            finally:
                self._busy = False

    def _dispatch_command(self, command: _Command, payload: dict) -> object:
        if command == _Command.PREWARM:
            self._handle_prewarm()
            return None
        if command == _Command.OPEN:
            self._handle_open(payload["start_url"], test_client=payload.get("test_client"))
            return None
        if command == _Command.QUICK_RECORD:
            if self._recording:
                raise RuntimeError("Запись уже идёт")
            self._handle_open(payload["start_url"], test_client=payload.get("test_client"))
            return self._handle_start_recording(payload["start_url"])
        if command == _Command.START_RECORDING:
            if self._recording:
                raise RuntimeError("Запись уже идёт")
            self._ensure_playwright(
                payload["start_url"],
                test_client=payload.get("test_client"),
            )
            return self._handle_start_recording(
                payload["start_url"],
                append=bool(payload.get("append")),
            )
        if command == _Command.STOP_RECORDING:
            return self._handle_stop_recording()
        if command == _Command.PAUSE_TOGGLE:
            return self._handle_pause_toggle()
        if command == _Command.UNDO_STEP:
            return self._handle_undo_step()
        if command == _Command.GET_URL:
            return self._handle_get_url()
        if command == _Command.FOCUS_BROWSER:
            return self._handle_focus_browser()
        if command == _Command.HIGHLIGHT:
            self._handle_highlight(payload["selector"])
            return None
        if command == _Command.CLEAR_HIGHLIGHT:
            self._handle_clear_highlight()
            return None
        if command == _Command.SET_FILTER:
            self._handle_set_filter(payload["enabled"])
            return None
        if command == _Command.SET_NAV_ONLY:
            self._handle_set_nav_only(payload["enabled"])
            return None
        if command == _Command.SET_HOVER_RECORD:
            self._handle_set_hover_record(payload["enabled"])
            return None
        if command == _Command.VALIDATE:
            return self._handle_validate(payload["scenario"], payload["on_log"])
        if command == _Command.PLAY:
            return self._handle_play(
                payload["scenario"],
                payload["on_log"],
                payload.get("on_step"),
                start_step=int(payload.get("start_step", 0)),
                end_step=payload.get("end_step"),
            )
        if command == _Command.CLOSE:
            self._handle_close()
            return None
        if command == _Command.SAVE_BROWSER_SESSION:
            return self._handle_save_browser_session(payload.get("label", ""))
        if command == _Command.BROWSER_SCRIPT and self._page:
            self._page.evaluate(payload["script"])
            return None
        if command == _Command.PICK_SELECTOR:
            return self._handle_pick_selector()
        if command == _Command.PICK_SELECTOR_CANCEL:
            self._handle_pick_selector_cancel()
            return None
        return None

    def _notify_complete(self, callback: object | None, result: object, command: _Command | None = None) -> None:
        if not callback:
            return
        if command == _Command.PICK_SELECTOR:
            callback(result)  # type: ignore[misc]
        elif result is not None:
            callback(result)  # type: ignore[misc]
        else:
            callback()  # type: ignore[misc]

    def _notify_error(self, callback: ErrorCallback | None, exc: Exception) -> None:
        if callback:
            callback(exc)

    def _handle_prewarm(self) -> None:
        configure_playwright_browsers()
        if self._playwright is None:
            self._playwright = sync_playwright().start()

    def _auth_key_for_url(self, start_url: str) -> tuple[str, str] | None:
        return auth_key(resolve_http_credentials(start_url, load_settings()))

    def _ensure_playwright(self, start_url: str = "", *, test_client: str | None = None) -> None:
        from app.feature_store import get_root
        from app.scenario_test_client import ensure_scenario_test_client

        configure_playwright_browsers()
        if test_client:
            ensure_scenario_test_client({"testClient": test_client}, get_root())

        wanted_key = self._auth_key_for_url(start_url)
        if (
            self._browser is not None
            and self._browser.is_connected()
            and start_url.strip()
            and wanted_key != self._context_auth_key
        ):
            self._close_session(keep_playwright=True)

        wanted_engine = load_browser_engine()
        if (
            self._browser is not None
            and self._browser.is_connected()
            and self._browser_engine is not None
            and self._browser_engine != wanted_engine
        ):
            self._close_session(keep_playwright=True)

        if self._playwright is None:
            self._emit_status("Инициализация Playwright...")
            self._playwright = sync_playwright().start()

        if self._browser is None or not self._browser.is_connected():
            label = wanted_engine.capitalize()
            self._emit_status(f"Запуск {label}...")
            self._browser = launch_browser(
                self._playwright,
                engine=wanted_engine,
                headless=False,
                on_status=self._emit_status,
            )
            self._browser_engine = wanted_engine

        if self._context is None or self._context_test_client != test_client:
            self._open_browser_context(start_url, test_client=test_client, wanted_key=wanted_key)

    def _open_browser_context(
        self,
        start_url: str,
        *,
        test_client: str | None,
        wanted_key: tuple[str, str] | None,
    ) -> None:
        from app.feature_store import get_root

        if self._browser is None:
            raise RuntimeError("Браузер не запущен")
        if self._context is not None:
            try:
                self._context.close()
            except Exception:  # noqa: BLE001
                pass
        context_options = browser_context_options(
            start_url,
            test_client=test_client,
            project_root=get_root(),
        )
        self._context = self._browser.new_context(**context_options)
        self._context_auth_key = wanted_key
        self._context_test_client = test_client
        self._context.on("page", setup_highlight_cleanup)
        self._page = self._context.new_page()
        setup_highlight_cleanup(self._page)
        self._context_binding_attached = False
        self._picker_binding_attached = False
        self._hooked_page_ids = set()
        self._browser_open = True
        self._watchers_attached = False
        self._attach_session_watchers()

    def _recorder_flags_script(self) -> str:
        settings = load_settings()
        min_ms = int(settings.get("hover_record_min_ms", 300))
        scroll_before = bool(settings.get("scroll_before_click"))
        return (
            f"window.__shopRecorderFilterMode = {'true' if self._filter_mode else 'false'};"
            f"window.__shopRecorderNavOnlyMode = {'true' if self._nav_only_mode else 'false'};"
            f"window.__shopRecorderHoverMode = {'true' if self._hover_record_mode else 'false'};"
            f"window.__shopRecorderHoverMinMs = {min_ms};"
            f"window.__shopRecorderScrollBeforeClick = {'true' if scroll_before else 'false'};"
        )

    def _sync_recorder_flags(self) -> None:
        if self._context is None:
            return
        script = self._recorder_flags_script()
        try:
            for page in self._context.pages:
                if not page.is_closed():
                    page.evaluate(script)
        except Exception:
            pass

    def _sync_filter_mode(self) -> None:
        self._sync_recorder_flags()

    def _inject_recorder_into_frame(self, frame) -> None:
        try:
            if frame.evaluate(RECORDER_INSTALLED_CHECK):
                frame.evaluate(self._recorder_flags_script())
                return
            frame.evaluate(self._recorder_flags_script())
            frame.evaluate(RECORDER_INIT_SCRIPT)
        except Exception:
            pass

    def _inject_recorder_into_page(self, page: Page) -> None:
        for frame in page.frames:
            self._inject_recorder_into_frame(frame)

    def _setup_page_listeners(self, page: Page) -> None:
        page_id = id(page)
        if page_id in self._hooked_page_ids:
            return
        self._hooked_page_ids.add(page_id)
        setup_highlight_cleanup(page)

        def on_nav(frame) -> None:
            self._inject_recorder_into_frame(frame)
            if self._recording and frame == page.main_frame:
                try:
                    url = page.url
                    if url and url not in {"", "about:blank"}:
                        self._step_inbox.put({"action": "goto", "url": url})
                except Exception:
                    pass

        def on_frame_attached(frame) -> None:
            self._inject_recorder_into_frame(frame)

        page.on("framenavigated", on_nav)
        page.on("frameattached", on_frame_attached)

    def _prepare_page_for_recording(self, page: Page) -> None:
        self._setup_page_listeners(page)
        self._watch_page_close(page)
        self._inject_recorder_into_page(page)

    def _attach_recording_hooks(self) -> None:
        if self._context is None or self._page is None:
            return

        if not self._context_binding_attached:
            self._context.expose_function("recordStep", self._enqueue_browser_step)
            self._context.add_init_script(
                f"{self._recorder_flags_script()}\n"
                f"{RECORDER_INIT_SCRIPT}"
            )
            self._context.on("page", self._prepare_page_for_recording)
            self._context_binding_attached = True

        for page in self._context.pages:
            self._prepare_page_for_recording(page)
        self._sync_filter_mode()

    def _navigate_if_needed(self, start_url: str) -> None:
        assert self._page is not None
        from app.http_auth import strip_url_credentials

        start_url = strip_url_credentials(start_url)
        if not start_url:
            return
        current_url = self._page.url
        if not current_url or current_url == "about:blank":
            self._emit_status(f"Открываю {start_url}...")
            self._page.goto(start_url, wait_until=NAV_WAIT_UNTIL, timeout=NAV_TIMEOUT_MS)

    def _handle_open(self, start_url: str, *, test_client: str | None = None) -> None:
        self._emit_status("Запуск браузера...")
        self._ensure_playwright(start_url, test_client=test_client)
        self._navigate_if_needed(start_url)
        if test_client:
            self._emit_status(f"Браузер открыт с TestClient «{test_client}».")
        else:
            self._emit_status("Браузер открыт (чистый сеанс). Перейдите на нужную страницу и нажмите «Начать запись».")

    def _handle_start_recording(self, start_url: str, *, append: bool = False) -> str:
        self._append_mode = append
        self._emit_status("Подготовка дозаписи..." if append else "Подготовка записи...")
        self._ensure_playwright(start_url, test_client=self._context_test_client)
        from app.http_auth import strip_url_credentials

        start_url = strip_url_credentials(start_url)
        page = self._get_active_page()
        current_url = page.url
        is_blank = not current_url or current_url == "about:blank"
        if is_blank and start_url:
            self._emit_status(f"Открываю {start_url}...")
            page.goto(start_url, wait_until=NAV_WAIT_UNTIL, timeout=NAV_TIMEOUT_MS)
            page = self._get_active_page()
        self._page = page
        self._recording = True
        self._paused = False
        self._attach_recording_hooks()
        if not append:
            self._append_step({"action": "goto", "url": page.url})
        status = "Дозапись идёт" if append else "Запись идёт"
        if self._filter_mode:
            status += " (только важные действия)"
        if self._paused:
            status += " — пауза"
        self._emit_status(f"{status}. Нажмите «Остановить запись».")
        return page.url

    def _handle_stop_recording(self) -> list[dict]:
        self._pump_playwright()
        self._drain_step_inbox()
        steps = normalize_steps(list(self._steps))
        self._recording = False
        self._paused = False
        self._emit_status(f"Запись остановлена. Шагов: {len(steps)}. Браузер остаётся открытым.")
        return steps

    def _handle_pause_toggle(self) -> bool:
        if not self._recording:
            raise RuntimeError("Запись не активна")
        self._paused = not self._paused
        if self._paused:
            self._emit_status("Запись на паузе")
        else:
            self._emit_status("Запись продолжена")
        return self._paused

    def _handle_undo_step(self) -> list[dict]:
        if not self._recording:
            raise RuntimeError("Запись не активна")
        if self._steps:
            self._steps.pop()
            if self._steps and self._steps[-1].get("action") == "goto":
                self._last_goto = self._steps[-1].get("url", "")
            elif not self._steps:
                self._last_goto = ""
        return list(self._steps)

    def _handle_get_url(self) -> str:
        if not self._browser or not self._browser.is_connected():
            raise RuntimeError("Браузер не открыт")
        page = self._get_active_page()
        return page.url

    def _handle_save_browser_session(self, name: str) -> str:
        from app.feature_store import get_root
        from app.test_clients import save_test_client_from_context

        if self._context is None or not self._browser or not self._browser.is_connected():
            raise RuntimeError("Браузер не открыт")
        client_name = str(name or "").strip()
        if not client_name:
            raise RuntimeError("Укажите имя TestClient")
        path = save_test_client_from_context(
            self._context,
            client_name,
            label=client_name,
            project_root=get_root(),
        )
        return str(path)

    def _handle_focus_browser(self) -> str:
        if self._context is None or not self._browser or not self._browser.is_connected():
            raise RuntimeError("Браузер не открыт")
        _ok, title = focus_browser_context_with_title(self._context)
        return title

    def _handle_highlight(self, selector: str) -> None:
        if not self._browser or not self._browser.is_connected():
            raise RuntimeError("Браузер не открыт")
        page = self._get_active_page()
        setup_highlight_cleanup(page)
        if not highlight_selector(page, selector):
            raise RuntimeError(f"Элемент не найден: {selector}")

    def _handle_clear_highlight(self) -> None:
        if not self._browser or not self._browser.is_connected():
            return
        remove_highlight(self._get_active_page())

    def _handle_set_filter(self, enabled: bool) -> None:
        self._filter_mode = enabled
        self._sync_recorder_flags()

    def _handle_set_nav_only(self, enabled: bool) -> None:
        self._nav_only_mode = enabled
        self._sync_recorder_flags()

    def _handle_set_hover_record(self, enabled: bool) -> None:
        self._hover_record_mode = enabled
        self._sync_recorder_flags()

    def _handle_validate(self, scenario: dict, on_log: Callable[[str], None]) -> dict[str, Any]:
        if not self._browser or not self._browser.is_connected():
            raise RuntimeError("Сначала откройте браузер")
        page = self._get_active_page()
        self._emit_status("Проверка сценария...")
        from app.selector_validate import (
            validate_results_to_issues,
            validate_results_to_payload,
            validate_scenario_selectors,
        )

        results = validate_scenario_selectors(page, scenario, on_log=on_log)
        issues = validate_results_to_issues(results)
        if issues:
            self._emit_status(f"Найдено проблем: {len(issues)}")
        else:
            self._emit_status("Сценарий прошёл проверку")
        return {
            "issues": issues,
            "results": validate_results_to_payload(results),
        }

    def _get_active_page(self) -> Page:
        if self._context is None:
            raise RuntimeError("Браузер не открыт")

        for page in reversed(self._context.pages):
            try:
                if page.is_closed():
                    continue
                if page.evaluate("document.hasFocus()"):
                    self._page = page
                    return page
            except Exception:
                continue

        if self._page and not self._page.is_closed():
            return self._page

        pages = [page for page in self._context.pages if not page.is_closed()]
        if not pages:
            raise RuntimeError("Нет открытых вкладок")
        self._page = pages[-1]
        return self._page

    def _attach_picker_bindings(self) -> None:
        if self._context is None:
            return
        if not self._picker_binding_attached:
            self._context.expose_function("pickSelectorDone", self._on_pick_selector_done)
            self._context.expose_function("pickSelectorCancel", self._on_pick_selector_cancel)
            self._picker_binding_attached = True

    def _on_pick_selector_done(self, selector: str) -> None:
        self._picker_result.put(str(selector))

    def _on_pick_selector_cancel(self) -> None:
        self._picker_result.put(None)

    def _uninstall_picker(self) -> None:
        page = self._page
        if page is None or page.is_closed():
            return
        uninstall_picker_from_all_frames(page)

    def _drain_picker_result(self) -> None:
        while True:
            try:
                self._picker_result.get_nowait()
            except queue.Empty:
                break

    def _abort_pick_if_interrupted(self) -> bool:
        """Handle cancel/close queued while picker wait loop is active."""
        while True:
            try:
                command, payload, on_complete, on_error = self._commands.get_nowait()
            except queue.Empty:
                return False
            if command == _Command.PICK_SELECTOR_CANCEL:
                self._handle_pick_selector_cancel()
                return True
            if command == _Command.CLOSE:
                self._handle_pick_selector_cancel()
                self._commands.put((command, payload, on_complete, on_error))
                return True
            if command == _Command.SHUTDOWN:
                self._handle_pick_selector_cancel()
                self._commands.put((command, payload, on_complete, on_error))
                return True
            self._commands.put((command, payload, on_complete, on_error))
            return False

    def _handle_pick_selector(self) -> str | None:
        if self._recording and not self._paused:
            raise RuntimeError("Остановите запись перед выбором элемента")
        if self._playing:
            raise RuntimeError("Дождитесь окончания воспроизведения")
        if not self._browser or not self._browser.is_connected():
            raise RuntimeError("Сначала откройте браузер")

        if self._pick_cancel_requested:
            self._pick_cancel_requested = False
            self._uninstall_picker()
            return None

        page = self._get_active_page()
        self._attach_picker_bindings()
        self._drain_picker_result()
        self._emit_status("Выбор элемента — кликните в браузере, Esc — отмена")

        def on_frame_navigated(frame) -> None:
            if frame != page.main_frame:
                return
            self._handle_pick_selector_cancel()
            try:
                self._picker_result.put_nowait(None)
            except queue.Full:
                pass

        page.on("framenavigated", on_frame_navigated)
        install_picker_in_all_frames(page)

        deadline = time.time() + 300
        try:
            while time.time() < deadline:
                try:
                    selector = self._picker_result.get(timeout=0.05)
                    self._uninstall_picker()
                    if selector:
                        self._emit_status(f"Выбран селектор: {selector}")
                    else:
                        self._emit_status("Выбор элемента отменён")
                    return selector
                except queue.Empty:
                    if self._abort_pick_if_interrupted():
                        self._uninstall_picker()
                        return None
                    self._pump_playwright()
        finally:
            try:
                page.remove_listener("framenavigated", on_frame_navigated)
            except Exception:
                pass

        self._uninstall_picker()
        raise RuntimeError("Время выбора элемента истекло")

    def _handle_pick_selector_cancel(self) -> None:
        self._pick_cancel_requested = True
        self._uninstall_picker()
        try:
            self._picker_result.put_nowait(None)
        except queue.Full:
            pass

    def _handle_play(
        self,
        scenario: dict,
        on_log: Callable[[str], None],
        on_step: Callable[[int, dict], None] | None = None,
        *,
        start_step: int = 0,
        end_step: int | None = None,
    ) -> PlayResult:
        if self._recording:
            raise RuntimeError("Остановите запись перед запуском теста")

        from app.feature_store import get_root
        from app.scenario_test_client import ensure_scenario_test_client, scenario_test_client_name

        wanted_client = scenario_test_client_name(scenario)
        if wanted_client:
            ensure_scenario_test_client(scenario, get_root())

        start_url = str(scenario.get("startUrl") or "")
        if not start_url:
            steps = scenario.get("steps") or []
            if steps and steps[0].get("action") == "goto":
                start_url = str(steps[0].get("url") or "")

        self._ensure_playwright(start_url, test_client=wanted_client)
        self._navigate_if_needed(start_url)

        if not self._browser or not self._browser.is_connected():
            raise RuntimeError("Не удалось открыть браузер")

        page = self._get_active_page()
        self._emit_status("Воспроизведение в открытом браузере...")
        if wanted_client:
            on_log(f"TestClient: {wanted_client}")
        on_log(f"Активная вкладка: {page.url}")

        self._playing = True
        self._stop_playback.clear()

        def close_session() -> None:
            self._handle_close()
            if self._on_browser_lost:
                self._on_browser_lost()

        try:
            result = run_scenario_on_page(
                page,
                scenario,
                on_log,
                stop_event=self._stop_playback,
                highlight=True,
                screenshot_on_error=True,
                on_step=on_step,
                trace_context=self._context,
                on_close_browser=close_session,
                start_step=start_step,
                end_step=end_step,
            )
        finally:
            self._playing = False
            self._stop_playback.clear()
            self._drain_step_inbox()

        self._emit_status(result["message"])
        return result

    def _handle_browser_disconnected(self) -> None:
        if self._session_releasing:
            return
        if not self._browser_open and self._browser is None:
            return
        was_open = self._browser_open or self._browser is not None
        self._recording = False
        self._paused = False
        self._playing = False
        self._browser = None
        self._context = None
        self._page = None
        self._context_binding_attached = False
        self._picker_binding_attached = False
        self._hooked_page_ids = set()
        self._watchers_attached = False
        reset_highlight_cleanup_state()
        self._browser_open = False
        if was_open and self._on_browser_lost:
            self._on_browser_lost()

    def _handle_close(self) -> None:
        self._recording = False
        self._paused = False
        self._close_session()
        self._emit_status("Браузер закрыт.")

    def _close_session(self, *, keep_playwright: bool = False) -> None:
        if self._session_releasing:
            return
        self._session_releasing = True
        playwright = self._playwright
        browser = self._browser
        context = self._context
        page = self._page
        self._browser = None
        self._context = None
        self._page = None
        self._context_binding_attached = False
        self._picker_binding_attached = False
        self._hooked_page_ids = set()
        reset_highlight_cleanup_state()
        self._browser_open = False
        self._watchers_attached = False
        self._context_auth_key = None
        self._context_test_client = None
        try:
            release_playwright_session(
                playwright=playwright,
                browser=browser,
                context=context,
                stop_driver=not keep_playwright,
                before_close=lambda: self._uninstall_picker_on_page(page),
            )
        finally:
            if not keep_playwright:
                self._playwright = None
            self._session_releasing = False

    def _uninstall_picker_on_page(self, page: Page | None) -> None:
        if page is None or page.is_closed():
            return
        uninstall_picker_from_all_frames(page)
