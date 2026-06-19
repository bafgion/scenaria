"""Tests for bringing Playwright browser windows to the foreground."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

from app.browser_focus import focus_browser_context


def test_focus_browser_context_uses_last_open_page() -> None:
    page1 = MagicMock()
    page1.is_closed.return_value = False
    page2 = MagicMock()
    page2.is_closed.return_value = False
    context = MagicMock()
    context.pages = [page1, page2]
    cdp = MagicMock()
    context.new_cdp_session.return_value = cdp

    assert focus_browser_context(context) is True

    page2.bring_to_front.assert_called_once()
    cdp.send.assert_called_once_with("Page.bringToFront")
    page2.evaluate.assert_called_once_with("() => window.focus()")


def test_focus_browser_context_without_pages() -> None:
    context = MagicMock()
    context.pages = []

    assert focus_browser_context(context) is False


def test_activate_browser_window_ui_thread_non_windows() -> None:
    from app.browser_focus import activate_browser_window_ui_thread

    if sys.platform == "win32":
        return
    assert activate_browser_window_ui_thread("Example") is False
