"""Background browser worker, picker queue, and play thread (T8b)."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from app.browser_config import browser_context_options, launch_browser, load_browser_engine
from app.paths import configure_playwright_browsers
from app.player_highlight import remove_highlight
from app.player_run import run_scenario_on_page
from app.player_types import (
    _PICK_CANCEL,
    ErrorCallback,
    LogCallback,
    PickerCallback,
    PlayResult,
)
from app.playwright_lifecycle import release_playwright_session
from app.selector_picker import SelectorPickerSession


class ScenarioPlayer:
    """Owns the Playwright thread, picker queue, and browser session lifecycle."""

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
