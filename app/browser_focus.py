"""Bring Playwright browser windows to the foreground."""

from __future__ import annotations

from playwright.sync_api import BrowserContext, Page


def _preferred_page(context: BrowserContext) -> Page | None:
    pages = [page for page in context.pages if not page.is_closed()]
    if not pages:
        return None
    return pages[-1]


def focus_browser_context(context: BrowserContext) -> bool:
    page = _preferred_page(context)
    if page is None:
        return False

    try:
        page.bring_to_front()
    except Exception:  # noqa: BLE001
        pass

    try:
        session = context.new_cdp_session(page)
        session.send("Page.bringToFront")
    except Exception:  # noqa: BLE001
        pass

    try:
        page.evaluate("() => window.focus()")
    except Exception:  # noqa: BLE001
        pass

    return True
