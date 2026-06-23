"""Shared Chromium launch settings for recorder and player."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

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

BROWSER_ENGINES: tuple[str, ...] = ("chromium", "firefox", "webkit")

BROWSER_ENGINE_LABELS: dict[str, str] = {
    "chromium": "Chromium",
    "firefox": "Firefox",
    "webkit": "WebKit (Safari)",
}


def normalize_browser_engine(value: str | None) -> str:
    engine = str(value or "chromium").strip().lower()
    if engine not in BROWSER_ENGINES:
        return "chromium"
    return engine


def load_browser_engine(settings: dict[str, Any] | None = None) -> str:
    if settings is None:
        from app.settings import load_settings

        settings = load_settings()
    return normalize_browser_engine(settings.get("browser_engine"))


def launch_browser(
    playwright,
    *,
    engine: str | None = None,
    headless: bool = False,
    slow_mo_ms: int = 0,
    settings: dict[str, Any] | None = None,
    on_status: Callable[[str], None] | None = None,
):
    resolved = normalize_browser_engine(engine) if engine else load_browser_engine(settings)
    from app.paths import configure_playwright_browsers
    from app.playwright_browsers import ensure_browser_engine

    ensure_browser_engine(resolved, on_line=on_status)
    configure_playwright_browsers(engine=resolved)
    launcher = getattr(playwright, resolved)
    kwargs: dict[str, Any] = {"headless": headless}
    if slow_mo_ms > 0:
        kwargs["slow_mo"] = slow_mo_ms
    if resolved == "chromium" and not headless:
        kwargs["args"] = BROWSER_LAUNCH_ARGS
    return launcher.launch(**kwargs)


def browser_context_options(
    url: str = "",
    *,
    headless: bool = False,
    settings: dict[str, Any] | None = None,
    project_root: Path | None = None,
    test_client: str | None = None,
) -> dict[str, Any]:
    """Playwright context options, including HTTP Basic Auth and optional TestClient."""
    if settings is None:
        from app.settings import load_settings

        settings = load_settings()

    options: dict[str, Any] = {} if headless else dict(BROWSER_CONTEXT_OPTIONS)
    credentials = playwright_http_credentials(url, settings)
    if credentials:
        options["http_credentials"] = credentials

    if test_client:
        from app.test_clients import require_test_client
        from app.feature_store import get_root

        root = project_root or get_root()
        options["storage_state"] = require_test_client(test_client, root)
    return options
