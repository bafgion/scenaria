"""Run a scenario on an open Playwright page (T8b)."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Page

from app.player_context import prepare_run_context
from app.player_highlight import remove_highlight, setup_highlight_cleanup
from app.player_step_executor import execute_step
from app.player_trace import (
    capture_failure_screenshot,
    start_play_trace,
    stop_play_trace,
)
from app.player_types import (
    BetweenStepsCallback,
    CloseBrowserCallback,
    LogCallback,
    PlayResult,
    StepCallback,
)
from app.steps import NAV_TIMEOUT_MS, NAV_WAIT_UNTIL, normalize_steps, urls_match


def validate_scenario_on_page(page: Page, scenario: dict[str, Any], on_log: LogCallback | None = None) -> list[str]:
    from app.selector_validate import validate_results_to_issues, validate_scenario_selectors

    results = validate_scenario_selectors(page, scenario, on_log=on_log)
    return validate_results_to_issues(results)


def run_scenario_on_page(
    page: Page,
    scenario: dict,
    on_log: LogCallback,
    *,
    stop_event: threading.Event | None = None,
    focus_event: threading.Event | None = None,
    highlight: bool = True,
    interactive: bool = True,
    screenshot_on_error: bool = True,
    on_step: StepCallback | None = None,
    on_close_browser: CloseBrowserCallback | None = None,
    on_between_steps: BetweenStepsCallback | None = None,
    trace_context=None,
    start_step: int = 0,
    end_step: int | None = None,
    run_initial_goto: bool = True,
    project_root: Path | None = None,
) -> PlayResult:
    log_lines: list[str] = []

    def _log(message: str) -> None:
        log_lines.append(message)
        on_log(message)

    steps = normalize_steps(list(scenario.get("steps", [])))
    total_steps = len(steps)
    if total_steps == 0:
        start_index = 0
        end_index = -1
    else:
        start_index = max(0, min(start_step, total_steps - 1))
        end_index = total_steps - 1 if end_step is None else max(0, min(end_step, total_steps - 1))
        if end_index < start_index:
            end_index = start_index

    start_url = scenario.get("startUrl") or (
        steps[0].get("url") if steps and steps[0].get("action") == "goto" else ""
    )
    scenario_name = str(scenario.get("name", ""))

    if trace_context is not None:
        start_play_trace(trace_context, scenario_name=scenario_name)

    if start_index > 0 and end_index >= start_index:
        _log(
            f"Запуск теста «{scenario_name}» (шаги {start_index + 1}–{end_index + 1} из {total_steps})"
        )
        _log(f"Пропуск шагов 1–{start_index}")
    elif total_steps:
        _log(f"Запуск теста «{scenario_name}» ({total_steps} шагов)")

    run_context = prepare_run_context(scenario, page, project_root=project_root)
    setup_highlight_cleanup(page)

    def _maybe_focus_browser() -> None:
        if focus_event is None or not focus_event.is_set():
            return
        focus_event.clear()
        from app.browser_focus import focus_browser_context

        focus_browser_context(page.context)

    if start_index == 0 and start_url and not urls_match(page.url, start_url):
        _log(f"Открываю {start_url}")
        remove_highlight(page)
        page.goto(start_url, wait_until=NAV_WAIT_UNTIL, timeout=NAV_TIMEOUT_MS)
    elif start_index > 0 and run_initial_goto:
        for prep_step in steps:
            if prep_step.get("action") == "goto":
                url = str(prep_step.get("url", "") or "")
                if url and not urls_match(page.url, url):
                    _log(f"Подготовка: открываю {url}")
                    remove_highlight(page)
                    page.goto(url, wait_until=NAV_WAIT_UNTIL, timeout=NAV_TIMEOUT_MS)
                break

    playable: list[tuple[int, dict]] = []
    for step_index, step in enumerate(steps):
        if step_index < start_index or step_index > end_index:
            continue
        if (
            step_index == 0
            and step.get("action") == "goto"
            and urls_match(page.url, step.get("url", ""))
        ):
            continue
        playable.append((step_index, step))

    skipped_count = total_steps - len(playable)
    executed = 0
    step_results: list[dict[str, Any]] = []
    for display_index, (step_index, step) in enumerate(playable, start=1):
        _maybe_focus_browser()
        if on_between_steps is not None:
            on_between_steps(page)
        if stop_event and stop_event.is_set():
            remove_highlight(page)
            return {
                "success": False,
                "message": "Остановлено пользователем",
                "executed_count": executed,
                "total_count": len(playable),
                "skipped_count": skipped_count,
                "failed_step": None,
                "failed_step_index": None,
                "screenshot_path": None,
                "trace_path": None,
                "log_lines": log_lines,
                "step_results": step_results,
            }
        started = time.perf_counter()
        try:
            if on_step:
                on_step(display_index, step_index, step)
            page = run_context.current_page(page)
            execute_step(
                page,
                step,
                display_index,
                _log,
                highlight=highlight,
                interactive=interactive,
                prior_steps=steps[:step_index],
                on_close_browser=on_close_browser,
                run_context=run_context,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            step_results.append(
                {
                    "index": step_index,
                    "action": str(step.get("action", "") or ""),
                    "selector": str(step.get("selector", "") or step.get("url", "") or ""),
                    "success": True,
                    "message": "",
                    "duration_ms": duration_ms,
                }
            )
            executed += 1
            if step.get("action") == "close_browser":
                break
        except Exception as exc:  # noqa: BLE001
            duration_ms = int((time.perf_counter() - started) * 1000)
            step_results.append(
                {
                    "index": step_index,
                    "action": str(step.get("action", "") or ""),
                    "selector": str(step.get("selector", "") or step.get("url", "") or ""),
                    "success": False,
                    "message": str(exc),
                    "duration_ms": duration_ms,
                }
            )
            remove_highlight(page)
            screenshot_path = None
            trace_path = None
            if screenshot_on_error:
                screenshot_path = capture_failure_screenshot(page, scenario_name, display_index)
                if screenshot_path:
                    _log(f"Скриншот ошибки: {screenshot_path}")
            if trace_context is not None:
                trace_path = stop_play_trace(
                    trace_context,
                    keep=True,
                    scenario_name=scenario_name,
                    step_index=display_index,
                )
                if trace_path:
                    _log(f"Trace: {trace_path}")
            return {
                "success": False,
                "message": str(exc),
                "executed_count": executed,
                "total_count": len(playable),
                "skipped_count": skipped_count,
                "failed_step": display_index,
                "failed_step_index": step_index,
                "screenshot_path": screenshot_path,
                "trace_path": trace_path,
                "log_lines": log_lines,
                "step_results": step_results,
            }

    remove_highlight(page)
    if trace_context is not None:
        stop_play_trace(trace_context, keep=False, scenario_name=scenario_name, step_index=0)
    return {
        "success": True,
        "message": "Готово",
        "executed_count": executed,
        "total_count": len(playable),
        "skipped_count": skipped_count,
        "failed_step": None,
        "failed_step_index": None,
        "screenshot_path": None,
        "trace_path": None,
        "log_lines": log_lines,
        "step_results": step_results,
    }
