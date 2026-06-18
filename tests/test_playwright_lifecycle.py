"""Tests for graceful Playwright teardown."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from playwright.sync_api import sync_playwright

from app.paths import configure_playwright_browsers
from app.playwright_lifecycle import release_playwright_session

pytestmark = pytest.mark.integration


def test_release_playwright_session() -> None:
    configure_playwright_browsers()
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto("about:blank")
    release_playwright_session(playwright=playwright, browser=browser, context=context)


def test_release_playwright_session_calls_before_close() -> None:
    configure_playwright_browsers()
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    hook = MagicMock()
    release_playwright_session(
        playwright=playwright,
        browser=browser,
        context=context,
        before_close=hook,
    )
    hook.assert_called_once()


def test_release_playwright_session_skips_disconnected_browser() -> None:
    configure_playwright_browsers()
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    browser.close()
    release_playwright_session(playwright=playwright, browser=browser, context=context)
