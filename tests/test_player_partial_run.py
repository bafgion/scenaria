"""Tests for partial scenario playback."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.player import run_scenario_on_page


def test_run_from_step_skips_earlier_steps() -> None:
    page = MagicMock()
    page.url = "https://example.com"
    executed: list[int] = []

    def on_step(display_index: int, step_index: int, _step: dict) -> None:
        executed.append(step_index)

    scenario = {
        "name": "Partial",
        "steps": [
            {"action": "goto", "url": "https://example.com"},
            {"action": "click", "selector": "#one"},
            {"action": "click", "selector": "#two"},
        ],
    }
    logs: list[str] = []
    result = run_scenario_on_page(
        page,
        scenario,
        logs.append,
        highlight=False,
        interactive=False,
        screenshot_on_error=False,
        start_step=1,
        on_step=on_step,
    )
    assert result["success"] is True
    assert executed == [1, 2]
    assert any("Пропуск шагов 1–1" in line for line in logs)


def test_run_until_step_limits_execution() -> None:
    page = MagicMock()
    page.url = "about:blank"
    executed: list[int] = []

    def on_step(_display: int, step_index: int, _step: dict) -> None:
        executed.append(step_index)

    scenario = {
        "name": "Until",
        "steps": [
            {"action": "goto", "url": "https://example.com"},
            {"action": "click", "selector": "#one"},
            {"action": "click", "selector": "#two"},
        ],
    }
    result = run_scenario_on_page(
        page,
        scenario,
        lambda _msg: None,
        highlight=False,
        interactive=False,
        screenshot_on_error=False,
        end_step=0,
        on_step=on_step,
    )
    assert result["success"] is True
    assert executed == [0]
