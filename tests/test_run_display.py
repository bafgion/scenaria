"""Tests for play result formatting."""

from __future__ import annotations

from app.run_display import format_run_diff


def test_format_run_diff_uses_failed_step_index_when_goto_skipped() -> None:
    steps = [
        {"action": "goto", "url": "https://shop.com"},
        {"action": "click", "selector": "button.prev"},
        {"action": "prompt_email_code", "selector": "input.pin-digit", "digits": 6},
    ]
    result = {
        "executed_count": 2,
        "total_count": 2,
        "skipped_count": 1,
        "failed_step": 2,
        "failed_step_index": 2,
        "success": False,
        "message": "timeout",
    }
    text = format_run_diff(steps, result)
    assert "Шагов в сценарии: 3 (пропущено при запуске: 1)" in text
    assert "Ошибка на шаге: 2" in text
    assert "Код из почты" in text
    assert "input.pin-digit" in text
    assert "button.prev" not in text


def test_format_run_diff_without_skipped_steps() -> None:
    steps = [{"action": "click", "selector": "button"}]
    result = {"executed_count": 1, "total_count": 1, "skipped_count": 0, "success": True}
    text = format_run_diff(steps, result)
    assert "Шагов в сценарии: 1" in text
    assert "пропущено" not in text
