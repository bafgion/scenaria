"""Shared types and callbacks for playback (T8b)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from playwright.sync_api import Page

LogCallback = Callable[[str], None]
DoneCallback = Callable[[bool, str], None]
StepCallback = Callable[[int, int, dict], None]
CloseBrowserCallback = Callable[[], None]
BetweenStepsCallback = Callable[[Page], None]
PickerCallback = Callable[[str | None], None]
ErrorCallback = Callable[[Exception], None]

PICK_CANCEL = object()
# Legacy name used in tests and worker queue.
_PICK_CANCEL = PICK_CANCEL


class PlayResult(TypedDict):
    success: bool
    message: str
    executed_count: int
    total_count: int
    failed_step: int | None
    failed_step_index: int | None
    screenshot_path: str | None
    trace_path: str | None
    log_lines: list[str]
    step_results: list[dict[str, Any]]
