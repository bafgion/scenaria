"""Playwright trace and failure screenshots (T8b)."""

from __future__ import annotations

from datetime import datetime

from playwright.sync_api import Page

from app.paths import screenshots_dir, traces_dir


def capture_failure_trace(context, scenario_name: str, step_index: int) -> str | None:
    try:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in scenario_name)[:40] or "run"
        path = traces_dir() / f"{safe_name}-step{step_index}-{stamp}.zip"
        context.tracing.stop(path=str(path))
        return str(path)
    except Exception:
        return None


def start_play_trace(context, *, scenario_name: str) -> None:
    try:
        context.tracing.start(screenshots=True, snapshots=True, sources=True, title=scenario_name)
    except Exception:
        pass


def stop_play_trace(context, *, keep: bool, scenario_name: str, step_index: int) -> str | None:
    if keep:
        return capture_failure_trace(context, scenario_name, step_index)
    try:
        context.tracing.stop()
    except Exception:
        pass
    return None


def capture_failure_screenshot(page: Page, scenario_name: str, step_index: int) -> str | None:
    try:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in scenario_name)[:40] or "run"
        path = screenshots_dir() / f"{safe_name}-step{step_index}-{stamp}.png"
        page.screenshot(path=str(path), full_page=True)
        return str(path)
    except Exception:
        return None
