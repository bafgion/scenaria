"""Replay recorded scenarios."""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict

from playwright.sync_api import Page, sync_playwright

from app.browser_config import browser_context_options, launch_browser, load_browser_engine
from app.paths import configure_playwright_browsers, screenshots_dir, traces_dir
from app.player_context import (  # noqa: F401 — public re-exports
    RunContext,
    _evaluate_condition,
    prepare_run_context,
    resolve_email_for_code_prompt,
)
from app.player_highlight import (
    highlight_selector,
    remove_highlight,
    reset_highlight_cleanup_state,
    setup_highlight_cleanup,
)
from app.player_step_executor import execute_step
from app.player_step_helpers import (  # noqa: F401 — public re-exports
    _ASSERT_ACTIONS,
    _INTERACTIVE_ACTIONS,
    _NAV_ACTIONS,
    _PROMPT_ACTIONS,
    _SESSION_ACTIONS,
    _WAIT_ACTIONS,
    _locator_hidden_issues,
    _locator_issues,
    _locator_issues_for_code_input,
    fill_verification_code,
)
from app.playwright_lifecycle import release_playwright_session
from app.selector_picker import SelectorPickerSession
from app.steps import NAV_TIMEOUT_MS, NAV_WAIT_UNTIL, normalize_steps, urls_match

LogCallback = Callable[[str], None]
DoneCallback = Callable[[bool, str], None]
StepCallback = Callable[[int, int, dict], None]
CloseBrowserCallback = Callable[[], None]
BetweenStepsCallback = Callable[["Page"], None]
PickerCallback = Callable[[str | None], None]
ErrorCallback = Callable[[Exception], None]

_PICK_CANCEL = object()

__all__ = [
    "CloseBrowserCallback",
    "DoneCallback",
    "ErrorCallback",
    "LogCallback",
    "PickerCallback",
    "PlayResult",
    "ScenarioPlayer",
    "StepCallback",
    "RunContext",
    "_ASSERT_ACTIONS",
    "_INTERACTIVE_ACTIONS",
    "_NAV_ACTIONS",
    "_PICK_CANCEL",
    "_PROMPT_ACTIONS",
    "_SESSION_ACTIONS",
    "_WAIT_ACTIONS",
    "_evaluate_condition",
    "_locator_hidden_issues",
    "_locator_issues",
    "_locator_issues_for_code_input",
    "capture_failure_screenshot",
    "capture_failure_trace",
    "execute_step",
    "fill_verification_code",
    "highlight_selector",
    "remove_highlight",
    "reset_highlight_cleanup_state",
    "resolve_email_for_code_prompt",
    "run_scenario_on_page",
    "setup_highlight_cleanup",
    "start_play_trace",
    "stop_play_trace",
    "validate_scenario_on_page",
]


class PlayResult(TypedDict):
    success: bool
    message: str
    executed_count: int
    total_count: int
    failed_step: int | None
    failed_step_index: int | None
    screenshot_path: str | None
    trace_path: str | None
    log_lines: list[str]
    step_results: list[dict[str, Any]]


def capture_failure_trace(context, scenario_name: str, step_index: int) -> str | None:
    try:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in scenario_name)[:40] or "run"
        path = traces_dir() / f"{safe_name}-step{step_index}-{stamp}.zip"
        context.tracing.stop(path=str(path))
        return str(path)
    except Exception:
        return None


def start_play_trace(context, *, scenario_name: str) -> None:
    try:
        context.tracing.start(screenshots=True, snapshots=True, sources=True, title=scenario_name)
    except Exception:
        pass


def stop_play_trace(context, *, keep: bool, scenario_name: str, step_index: int) -> str | None:
    if keep:
        return capture_failure_trace(context, scenario_name, step_index)
    try:
        context.tracing.stop()
    except Exception:
        pass
    return None


def capture_failure_screenshot(page: Page, scenario_name: str, step_index: int) -> str | None:
    try:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in scenario_name)[:40] or "run"
        path = screenshots_dir() / f"{safe_name}-step{step_index}-{stamp}.png"
        page.screenshot(path=str(path), full_page=True)
        return str(path)
    except Exception:
        return None


def validate_scenario_on_page(page: Page, scenario: dict[str, Any], on_log: LogCallback | None = None) -> list[str]:
    from app.selector_validate import validate_results_to_issues, validate_scenario_selectors

    results = validate_scenario_selectors(page, scenario, on_log=on_log)
    return validate_results_to_issues(results)


def run_scenario_on_page(
    page: Page,
    scenario: dict,
    on_log: LogCallback,
    *,
    stop_event: threading.Event | None = None,
    focus_event: threading.Event | None = None,
    highlight: bool = True,
    interactive: bool = True,
    screenshot_on_error: bool = True,
    on_step: StepCallback | None = None,
    on_close_browser: CloseBrowserCallback | None = None,
    on_between_steps: BetweenStepsCallback | None = None,
    trace_context=None,
    start_step: int = 0,
    end_step: int | None = None,
    run_initial_goto: bool = True,
    project_root: Path | None = None,
) -> PlayResult:
    log_lines: list[str] = []

    def _log(message: str) -> None:
        log_lines.append(message)
        on_log(message)

    steps = normalize_steps(list(scenario.get("steps", [])))
    total_steps = len(steps)
    if total_steps == 0:
        start_index = 0
        end_index = -1
    else:
        start_index = max(0, min(start_step, total_steps - 1))
        end_index = total_steps - 1 if end_step is None else max(0, min(end_step, total_steps - 1))
        if end_index < start_index:
            end_index = start_index

    start_url = scenario.get("startUrl") or (
        steps[0].get("url") if steps and steps[0].get("action") == "goto" else ""
    )
    scenario_name = str(scenario.get("name", ""))

    if trace_context is not None:
        start_play_trace(trace_context, scenario_name=scenario_name)

    if start_index > 0 and end_index >= start_index:
        _log(
            f"Запуск теста «{scenario_name}» (шаги {start_index + 1}–{end_index + 1} из {total_steps})"
        )
        _log(f"Пропуск шагов 1–{start_index}")
    elif total_steps:
        _log(f"Запуск теста «{scenario_name}» ({total_steps} шагов)")

    run_context = prepare_run_context(scenario, page, project_root=project_root)
    setup_highlight_cleanup(page)

    def _maybe_focus_browser() -> None:
        if focus_event is None or not focus_event.is_set():
            return
        focus_event.clear()
        from app.browser_focus import focus_browser_context

        focus_browser_context(page.context)

    if start_index == 0 and start_url and not urls_match(page.url, start_url):
        _log(f"Открываю {start_url}")
        remove_highlight(page)
        page.goto(start_url, wait_until=NAV_WAIT_UNTIL, timeout=NAV_TIMEOUT_MS)
    elif start_index > 0 and run_initial_goto:
        for prep_step in steps:
            if prep_step.get("action") == "goto":
                url = str(prep_step.get("url", "") or "")
                if url and not urls_match(page.url, url):
                    _log(f"Подготовка: открываю {url}")
                    remove_highlight(page)
                    page.goto(url, wait_until=NAV_WAIT_UNTIL, timeout=NAV_TIMEOUT_MS)
                break

    playable: list[tuple[int, dict]] = []
    for step_index, step in enumerate(steps):
        if step_index < start_index or step_index > end_index:
            continue
        if (
            step_index == 0
            and step.get("action") == "goto"
            and urls_match(page.url, step.get("url", ""))
        ):
            continue
        playable.append((step_index, step))

    skipped_count = total_steps - len(playable)
    executed = 0
    step_results: list[dict[str, Any]] = []
    for display_index, (step_index, step) in enumerate(playable, start=1):
        _maybe_focus_browser()
        if on_between_steps is not None:
            on_between_steps(page)
        if stop_event and stop_event.is_set():
            remove_highlight(page)
            return {
                "success": False,
                "message": "Остановлено пользователем",
                "executed_count": executed,
                "total_count": len(playable),
                "skipped_count": skipped_count,
                "failed_step": None,
                "failed_step_index": None,
                "screenshot_path": None,
                "trace_path": None,
                "log_lines": log_lines,
                "step_results": step_results,
            }
        started = time.perf_counter()
        try:
            if on_step:
                on_step(display_index, step_index, step)
            page = run_context.current_page(page)
            execute_step(
                page,
                step,
                display_index,
                _log,
                highlight=highlight,
                interactive=interactive,
                prior_steps=steps[:step_index],
                on_close_browser=on_close_browser,
                run_context=run_context,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            step_results.append(
                {
                    "index": step_index,
                    "action": str(step.get("action", "") or ""),
                    "selector": str(step.get("selector", "") or step.get("url", "") or ""),
                    "success": True,
                    "message": "",
                    "duration_ms": duration_ms,
                }
            )
            executed += 1
            if step.get("action") == "close_browser":
                break
        except Exception as exc:  # noqa: BLE001
            duration_ms = int((time.perf_counter() - started) * 1000)
            step_results.append(
                {
                    "index": step_index,
                    "action": str(step.get("action", "") or ""),
                    "selector": str(step.get("selector", "") or step.get("url", "") or ""),
                    "success": False,
                    "message": str(exc),
                    "duration_ms": duration_ms,
                }
            )
            remove_highlight(page)
            screenshot_path = None
            trace_path = None
            if screenshot_on_error:
                screenshot_path = capture_failure_screenshot(page, scenario_name, display_index)
                if screenshot_path:
                    _log(f"Скриншот ошибки: {screenshot_path}")
            if trace_context is not None:
                trace_path = stop_play_trace(
                    trace_context,
                    keep=True,
                    scenario_name=scenario_name,
                    step_index=display_index,
                )
                if trace_path:
                    _log(f"Trace: {trace_path}")
            return {
                "success": False,
                "message": str(exc),
                "executed_count": executed,
                "total_count": len(playable),
                "skipped_count": skipped_count,
                "failed_step": display_index,
                "failed_step_index": step_index,
                "screenshot_path": screenshot_path,
                "trace_path": trace_path,
                "log_lines": log_lines,
                "step_results": step_results,
            }

    remove_highlight(page)
    if trace_context is not None:
        stop_play_trace(trace_context, keep=False, scenario_name=scenario_name, step_index=0)
    return {
        "success": True,
        "message": "Готово",
        "executed_count": executed,
        "total_count": len(playable),
        "skipped_count": skipped_count,
        "failed_step": None,
        "failed_step_index": None,
        "screenshot_path": None,
        "trace_path": None,
        "log_lines": log_lines,
        "step_results": step_results,
    }


class ScenarioPlayer:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._focus = threading.Event()
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._shutdown_done = False
        self._picker = SelectorPickerSession()
        self._pick_requests: queue.Queue[object] = queue.Queue()
        self._on_browser_lost: Callable[[], None] | None = None
        self._browser_lost_notified = False
        self._session_releasing = False

    def set_browser_lost_handler(self, handler: Callable[[], None] | None) -> None:
        self._on_browser_lost = handler

    @property
    def browser_open(self) -> bool:
        browser = self._browser
        if browser is None or not browser.is_connected():
            return False
        context = self._context
        if context is not None:
            return any(not page.is_closed() for page in context.pages)
        page = self._page
        return page is not None and not page.is_closed()

    @property
    def worker_alive(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    def play(
        self,
        scenario: dict,
        on_log: LogCallback,
        on_done: Callable[[PlayResult], None],
        *,
        headless: bool = False,
        slow_mo_ms: int = 200,
        on_started: Callable[[], None] | None = None,
        start_step: int = 0,
        end_step: int | None = None,
        project_root: Path | None = None,
    ) -> None:
        if self._thread and self._thread.is_alive():
            raise RuntimeError("Воспроизведение уже запущено")
        if self._thread is not None:
            self._release_detached_session()
            self._thread = None
        self._stop.clear()
        self._browser_lost_notified = False
        self._thread = threading.Thread(
            target=self._run,
            args=(
                scenario,
                on_log,
                on_done,
                headless,
                slow_mo_ms,
                on_started,
                start_step,
                end_step,
                project_root,
            ),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._pick_requests.put(_PICK_CANCEL)
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=30)
        self._release_detached_session()
        if thread is None or not thread.is_alive():
            self._thread = None

    def focus_browser(self) -> bool:
        if not self.browser_open or self._context is None:
            return False
        thread = self._thread
        if thread is not None and thread.is_alive():
            self._focus.set()
            return True
        from app.browser_focus import focus_browser_context

        return focus_browser_context(self._context)

    def pick_selector(
        self,
        on_complete: PickerCallback,
        on_error: ErrorCallback | None = None,
    ) -> None:
        if not self.browser_open:
            raise RuntimeError("Браузер теста не открыт")
        self._pick_requests.put((on_complete, on_error))

    def cancel_pick_selector(self) -> None:
        self._pick_requests.put(_PICK_CANCEL)

    def _cancel_pending_picks(self, page: Page) -> None:
        self._picker.cancel_active(page)
        while True:
            try:
                item = self._pick_requests.get_nowait()
            except queue.Empty:
                break
            if item is _PICK_CANCEL:
                continue
            on_complete, _on_error = item
            on_complete(None)

    def _active_page(self) -> Page:
        page = self._page
        if page is not None and not page.is_closed():
            return page
        context = self._context
        if context is None:
            raise RuntimeError("Браузер теста не открыт")
        pages = [item for item in context.pages if not item.is_closed()]
        if not pages:
            raise RuntimeError("Нет открытых вкладок")
        self._page = pages[-1]
        return self._page

    def _pick_pump(self, page: Page) -> None:
        if self._stop.is_set():
            self._picker.cancel_active(page)
            return
        try:
            item = self._pick_requests.get_nowait()
        except queue.Empty:
            item = None
        if item is _PICK_CANCEL:
            self._picker.cancel_active(page)
            return
        if item is not None:
            self._pick_requests.put(item)
        try:
            if not page.is_closed():
                page.wait_for_timeout(25)
        except Exception:
            pass

    def _service_pick_requests(self, page: Page) -> None:
        while True:
            try:
                item = self._pick_requests.get_nowait()
            except queue.Empty:
                return
            if item is _PICK_CANCEL:
                self._cancel_pending_picks(page)
                continue
            on_complete, on_error = item
            try:
                active = self._active_page()
                selector = self._picker.pick(
                    active,
                    active.context,
                    pump=lambda: self._pick_pump(active),
                )
                on_complete(selector)
            except Exception as exc:  # noqa: BLE001
                if on_error is not None:
                    on_error(exc)
                else:
                    on_complete(None)

    def _idle_loop(self, page: Page) -> None:
        while not self._stop.is_set() and self.browser_open:
            if self._poll_browser_lost():
                break
            try:
                active = self._active_page()
            except RuntimeError:
                self._handle_browser_disconnected()
                break
            if self._focus.is_set():
                self._focus.clear()
                from app.browser_focus import focus_browser_context

                focus_browser_context(active.context)
            self._service_pick_requests(active)
            if self._stop.is_set():
                break
            try:
                active.wait_for_timeout(50)
            except Exception:
                self._handle_browser_disconnected()
                break

    def _attach_session_watchers(self) -> None:
        browser = self._browser
        if browser is None:
            return
        try:
            browser.on("disconnected", lambda _: self._handle_browser_disconnected())
        except Exception:
            pass
        context = self._context
        if context is not None:
            try:
                context.on("close", lambda _: self._handle_browser_disconnected())
            except Exception:
                pass

    def _poll_browser_lost(self) -> bool:
        if self.browser_open:
            return False
        self._handle_browser_disconnected()
        return True

    def _handle_browser_disconnected(self) -> None:
        if self._session_releasing:
            return
        if self._browser is None and self._browser_lost_notified:
            return
        was_open = self._browser is not None
        self._browser = None
        self._context = None
        self._page = None
        if was_open and not self._browser_lost_notified:
            self._browser_lost_notified = True
            if self._on_browser_lost:
                self._on_browser_lost()

    def shutdown(self) -> None:
        if self._shutdown_done:
            return
        self._shutdown_done = True
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=15)
        self._release_detached_session()

    def _release_detached_session(self) -> None:
        if self._session_releasing:
            return
        self._session_releasing = True
        playwright = self._playwright
        browser = self._browser
        context = self._context
        page = self._page
        self._browser = None
        self._context = None
        self._playwright = None
        self._page = None
        try:
            release_playwright_session(
                playwright=playwright,
                browser=browser,
                context=context,
                before_close=lambda: self._picker.cancel_active(page),
            )
        finally:
            self._session_releasing = False

    def _run(
        self,
        scenario: dict,
        on_log: LogCallback,
        on_done: Callable[[PlayResult], None],
        headless: bool,
        slow_mo_ms: int,
        on_started: Callable[[], None] | None,
        start_step: int = 0,
        end_step: int | None = None,
        project_root: Path | None = None,
    ) -> None:
        configure_playwright_browsers()
        result: PlayResult
        session_closed = False
        playwright = None
        browser = None
        context = None
        page = None

        def close_session() -> None:
            nonlocal session_closed
            if session_closed:
                return
            session_closed = True
            self._session_releasing = True
            try:
                if page is not None:
                    remove_highlight(page)
                self._picker.cancel_active(page)
                release_playwright_session(
                    playwright=playwright,
                    browser=browser,
                    context=context,
                )
            finally:
                self._session_releasing = False
                self._browser = None
                self._context = None
                self._playwright = None
                self._page = None

        try:
            playwright = sync_playwright().start()
            engine = str(scenario.get("browserEngine") or "") or load_browser_engine()
            browser = launch_browser(
                playwright,
                engine=engine,
                headless=headless,
                slow_mo_ms=slow_mo_ms,
                on_status=on_log,
            )
            start_url = scenario.get("startUrl") or ""
            steps = scenario.get("steps") or []
            if not start_url and steps and steps[0].get("action") == "goto":
                start_url = str(steps[0].get("url") or "")
            from app.scenario_test_client import ensure_scenario_test_client

            test_client = ensure_scenario_test_client(scenario, project_root)
            context = browser.new_context(
                **browser_context_options(
                    start_url,
                    headless=headless,
                    project_root=project_root,
                    test_client=test_client,
                )
            )
            page = context.new_page()
            self._playwright = playwright
            self._browser = browser
            self._context = context
            self._page = page
            self._browser_lost_notified = False
            self._attach_session_watchers()
            if on_started is not None:
                on_started()

            result = run_scenario_on_page(
                page,
                scenario,
                on_log,
                stop_event=self._stop,
                focus_event=self._focus,
                highlight=not headless,
                interactive=not headless,
                trace_context=context,
                on_close_browser=close_session,
                on_between_steps=self._service_pick_requests,
                start_step=start_step,
                end_step=end_step,
                project_root=project_root,
            )
        except Exception as exc:  # noqa: BLE001
            result = {
                "success": False,
                "message": str(exc),
                "executed_count": 0,
                "total_count": len(scenario.get("steps", [])),
                "failed_step": None,
                "failed_step_index": None,
                "screenshot_path": None,
                "trace_path": None,
                "log_lines": [f"Ошибка: {exc}"],
                "step_results": [],
            }
            on_log(f"Ошибка: {exc}")

        on_done(result)

        if session_closed:
            return

        if page is None:
            return

        self._playwright = playwright
        self._browser = browser
        self._context = context
        self._page = page

        if headless:
            close_session()
            return

        if not result.get("success"):
            on_log(
                "Тест завершён с ошибкой. Браузер остаётся открытым — исправьте шаги и запустите снова."
            )
            self._idle_loop(page)
            if not session_closed and not self.browser_open:
                close_session()
            return

        on_log(
            "Тест завершён. Браузер остаётся открытым — добавьте шаг «закрываю браузер» для закрытия."
        )
        self._idle_loop(page)
        if not session_closed and not self.browser_open:
            close_session()
