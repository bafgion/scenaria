"""Tests for multi-browser configuration."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.browser_config import launch_browser, load_browser_engine, normalize_browser_engine


def test_normalize_browser_engine_defaults() -> None:
    assert normalize_browser_engine(None) == "chromium"
    assert normalize_browser_engine("firefox") == "firefox"
    assert normalize_browser_engine("unknown") == "chromium"


def test_load_browser_engine_from_settings() -> None:
    assert load_browser_engine({"browser_engine": "webkit"}) == "webkit"


def test_launch_browser_uses_engine(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.playwright_browsers.ensure_browser_engine",
        lambda engine, on_line=None: None,
    )
    playwright = MagicMock()
    chromium = MagicMock()
    firefox = MagicMock()
    playwright.chromium = chromium
    playwright.firefox = firefox
    launch_browser(playwright, engine="firefox", headless=True)
    firefox.launch.assert_called_once()
    chromium.launch.assert_not_called()
