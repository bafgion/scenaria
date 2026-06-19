"""Bring Playwright browser windows to the foreground."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from playwright.sync_api import BrowserContext, Page

if TYPE_CHECKING:
    from collections.abc import Callable


def _preferred_page(context: BrowserContext) -> Page | None:
    pages = [page for page in context.pages if not page.is_closed()]
    if not pages:
        return None
    return pages[-1]


def _safe_page_title(page: Page) -> str:
    try:
        return page.title().strip()
    except Exception:  # noqa: BLE001
        return ""


def _focus_via_cdp(context: BrowserContext, page: Page) -> None:
    try:
        page.bring_to_front()
    except Exception:  # noqa: BLE001
        pass

    try:
        session = context.new_cdp_session(page)
        session.send("Page.bringToFront")
    except Exception:  # noqa: BLE001
        pass

    browser = context.browser
    if browser is not None:
        try:
            browser_cdp = browser.new_browser_cdp_session()
            targets = browser_cdp.send("Target.getTargets")
            target_infos = targets.get("targetInfos", [])
            page_target_id = None
            for info in target_infos:
                if info.get("type") == "page" and not info.get("url", "").startswith("devtools://"):
                    page_target_id = info.get("targetId")
            if page_target_id:
                window = browser_cdp.send(
                    "Browser.getWindowForTarget",
                    {"targetId": page_target_id},
                )
                window_id = window.get("windowId")
                if window_id is not None:
                    bounds = browser_cdp.send("Window.getWindowBounds", {"windowId": window_id})
                    browser_cdp.send(
                        "Window.setWindowBounds",
                        {"windowId": window_id, "bounds": bounds["bounds"]},
                    )
        except Exception:  # noqa: BLE001
            pass

    try:
        page.evaluate("() => window.focus()")
    except Exception:  # noqa: BLE001
        pass


def focus_browser_context_with_title(context: BrowserContext) -> tuple[bool, str]:
    page = _preferred_page(context)
    if page is None:
        return False, ""

    title = _safe_page_title(page)
    _focus_via_cdp(context, page)
    return True, title


def focus_browser_context(context: BrowserContext) -> bool:
    ok, _title = focus_browser_context_with_title(context)
    return ok


def activate_browser_window_ui_thread(title_hint: str = "") -> bool:
    """Raise the Chromium window on the UI thread (after a user click in Scenaria)."""
    if sys.platform != "win32":
        return False
    return _windows_activate_chromium_window(title_hint)


def _windows_activate_chromium_window(title_hint: str) -> bool:
    hwnd = _find_chromium_hwnd(title_hint)
    if hwnd is None and title_hint:
        hwnd = _find_chromium_hwnd("")
    if hwnd is None:
        return False
    return _activate_hwnd(hwnd)


def _find_chromium_hwnd(title_hint: str) -> int | None:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    matches: list[int] = []
    hint = title_hint.casefold()

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def enum_proc(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, 256)
        if "Chrome_WidgetWin" not in class_name.value:
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        title_buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title_buff, length + 1)
        window_title = title_buff.value
        if hint and hint not in window_title.casefold():
            return True
        matches.append(hwnd)
        return True

    user32.EnumWindows(enum_proc, 0)
    if not matches:
        return None
    return matches[-1]


def _activate_hwnd(hwnd: int) -> bool:
    import ctypes

    user32 = ctypes.windll.user32
    SW_RESTORE = 9
    VK_MENU = 0x12
    KEYEVENTF_KEYUP = 0x0002

    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)

    user32.keybd_event(VK_MENU, 0, 0, 0)
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)

    user32.SetForegroundWindow(hwnd)
    user32.BringWindowToTop(hwnd)
    return bool(user32.GetForegroundWindow() == hwnd)
