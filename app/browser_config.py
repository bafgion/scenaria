"""Shared Chromium launch settings for recorder and player."""

from __future__ import annotations

from typing import Any

from app.http_auth import playwright_http_credentials

BROWSER_LAUNCH_ARGS = [
    "--disable-dev-shm-usage",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    "--start-maximized",
]

# Follow the real browser window size when the user resizes or maximizes.
BROWSER_CONTEXT_OPTIONS = {"viewport": None, "no_viewport": True}


def browser_context_options(
    url: str = "",
    *,
    headless: bool = False,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Playwright context options, including HTTP Basic Auth when configured."""
    if settings is None:
        from app.settings import load_settings

        settings = load_settings()

    options: dict[str, Any] = {} if headless else dict(BROWSER_CONTEXT_OPTIONS)
    credentials = playwright_http_credentials(url, settings)
    if credentials:
        options["http_credentials"] = credentials
    return options
