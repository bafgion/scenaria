"""Graceful Playwright session teardown (avoids EPIPE on the Node driver)."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

_SETTLE_AFTER_BROWSER_CLOSE_S = 0.2
_DISCONNECT_WAIT_TIMEOUT_S = 1.0


def release_playwright_session(
    *,
    playwright: Any | None = None,
    browser: Any | None = None,
    context: Any | None = None,
    stop_driver: bool = True,
    before_close: Callable[[], None] | None = None,
) -> None:
    """Close pages and browser, wait for disconnect, then stop the Playwright driver."""
    if before_close is not None:
        try:
            before_close()
        except Exception:
            pass

    pages: list[Any] = []
    if context is not None:
        try:
            pages = list(context.pages)
        except Exception:
            pages = []

    for page in pages:
        try:
            if not page.is_closed():
                page.close()
        except Exception:
            pass

    browser_was_connected = False
    if browser is not None:
        try:
            browser_was_connected = browser.is_connected()
        except Exception:
            browser_was_connected = False

    if browser is not None and browser_was_connected:
        try:
            browser.close()
        except Exception:
            pass
        _wait_for_browser_disconnect(browser)
    elif context is not None:
        try:
            context.close()
        except Exception:
            pass

    if browser_was_connected or context is not None:
        time.sleep(_SETTLE_AFTER_BROWSER_CLOSE_S)

    if stop_driver and playwright is not None:
        try:
            playwright.stop()
        except Exception:
            pass


def _wait_for_browser_disconnect(browser: Any) -> None:
    deadline = time.time() + _DISCONNECT_WAIT_TIMEOUT_S
    while time.time() < deadline:
        try:
            if not browser.is_connected():
                return
        except Exception:
            return
        time.sleep(0.02)
