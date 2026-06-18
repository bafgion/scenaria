"""In-browser selector picker for any Playwright page."""

from __future__ import annotations

import queue
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from app.picker_script import PICKER_INSTALL_SCRIPT, PICKER_UNINSTALL_SCRIPT

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, Page

PumpCallback = Callable[[], None] | None


class SelectorPickerSession:
    def __init__(self) -> None:
        self._results: queue.Queue[str | None] = queue.Queue()
        self._attached: set[int] = set()

    def attach(self, context: BrowserContext) -> None:
        context_id = id(context)
        if context_id in self._attached:
            return

        def done(selector: str) -> None:
            self._results.put(str(selector))

        def cancel() -> None:
            self._results.put(None)

        context.expose_function("pickSelectorDone", done)
        context.expose_function("pickSelectorCancel", cancel)
        self._attached.add(context_id)

    def drain(self) -> None:
        while True:
            try:
                self._results.get_nowait()
            except queue.Empty:
                return

    def cancel_active(self, page: Page | None) -> None:
        self._uninstall(page)
        try:
            self._results.put_nowait(None)
        except queue.Full:
            pass

    def pick(
        self,
        page: Page,
        context: BrowserContext,
        *,
        pump: PumpCallback = None,
        timeout: float = 300.0,
    ) -> str | None:
        self.attach(context)
        self.drain()
        page.evaluate(PICKER_INSTALL_SCRIPT)
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                selector = self._results.get(timeout=0.05)
                self._uninstall(page)
                return selector
            except queue.Empty:
                if pump is not None:
                    pump()
                elif not page.is_closed():
                    page.wait_for_timeout(50)
        self._uninstall(page)
        raise RuntimeError("Время выбора элемента истекло")

    def _uninstall(self, page: Page | None) -> None:
        if page is None or page.is_closed():
            return
        try:
            page.evaluate(PICKER_UNINSTALL_SCRIPT)
        except Exception:
            pass
