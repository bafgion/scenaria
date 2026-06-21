"""Browser tab resolution helpers for playback (A7)."""

from __future__ import annotations

from playwright.sync_api import BrowserContext, Page


def open_pages(context: BrowserContext) -> list[Page]:
    return [page for page in context.pages if not page.is_closed()]


def resolve_tab_page(
    context: BrowserContext,
    *,
    mode: str,
    value: str = "",
) -> Page | None:
    pages = open_pages(context)
    if not pages:
        return None

    normalized = str(mode or "").strip().lower()
    if normalized == "first":
        return pages[0]
    if normalized in {"last", "new"}:
        return pages[-1]
    if normalized == "title":
        needle = str(value or "").strip().lower()
        for page in pages:
            try:
                title = page.title() or ""
            except Exception:  # noqa: BLE001
                title = ""
            if needle in title.lower():
                return page
        return None
    if normalized == "url":
        needle = str(value or "").strip().lower()
        for page in pages:
            if needle in page.url.lower():
                return page
        return None
    if normalized == "index":
        try:
            index = int(value)
        except (TypeError, ValueError):
            return None
        if 0 <= index < len(pages):
            return pages[index]
        return None
    return None
