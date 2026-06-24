"""Replay recorded scenarios — public facade (T8b)."""

from __future__ import annotations

from app.player_context import (  # noqa: F401 — public re-exports
    RunContext,
    _evaluate_condition,
    prepare_run_context,
    resolve_email_for_code_prompt,
)
from app.player_highlight import (  # noqa: F401
    _maybe_highlight,
    highlight_selector,
    remove_highlight,
    reset_highlight_cleanup_state,
    setup_highlight_cleanup,
)
from app.player_run import run_scenario_on_page, validate_scenario_on_page
from app.player_step_executor import execute_step
from app.player_step_helpers import (  # noqa: F401
    _ASSERT_ACTIONS,
    _INTERACTIVE_ACTIONS,
    _NAV_ACTIONS,
    _PROMPT_ACTIONS,
    _SESSION_ACTIONS,
    _WAIT_ACTIONS,
    _locator_hidden_issues,
    _locator_issues,
    _locator_issues_for_code_input,
    fill_verification_code,
)
from app.player_trace import (
    capture_failure_screenshot,
    capture_failure_trace,
    start_play_trace,
    stop_play_trace,
)
from app.player_types import (
    _PICK_CANCEL,
    BetweenStepsCallback,
    CloseBrowserCallback,
    DoneCallback,
    ErrorCallback,
    LogCallback,
    PickerCallback,
    PlayResult,
    StepCallback,
)
from app.player_worker import ScenarioPlayer
from app.steps import urls_match

__all__ = [
    "BetweenStepsCallback",
    "CloseBrowserCallback",
    "DoneCallback",
    "ErrorCallback",
    "LogCallback",
    "PickerCallback",
    "PlayResult",
    "RunContext",
    "ScenarioPlayer",
    "StepCallback",
    "_ASSERT_ACTIONS",
    "_INTERACTIVE_ACTIONS",
    "_NAV_ACTIONS",
    "_PICK_CANCEL",
    "_PROMPT_ACTIONS",
    "_SESSION_ACTIONS",
    "_WAIT_ACTIONS",
    "_evaluate_condition",
    "_locator_hidden_issues",
    "_locator_issues",
    "_locator_issues_for_code_input",
    "_maybe_highlight",
    "capture_failure_screenshot",
    "capture_failure_trace",
    "execute_step",
    "fill_verification_code",
    "highlight_selector",
    "remove_highlight",
    "reset_highlight_cleanup_state",
    "resolve_email_for_code_prompt",
    "run_scenario_on_page",
    "setup_highlight_cleanup",
    "start_play_trace",
    "stop_play_trace",
    "urls_match",
    "validate_scenario_on_page",
]
