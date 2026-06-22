"""Tests for run result display helpers."""

from __future__ import annotations

from app.run_result_display import (
    format_failed_step_label,
    format_runner_label,
    format_run_status_text,
    format_single_run_summary,
    summarize_run_history,
    summarize_suite_cases,
)
from app.run_status_store import RunHistoryEntry


def test_format_runner_label() -> None:
    assert format_runner_label("playwright") == "Playwright"
    assert format_runner_label("vanessa") == "Vanessa Automation"
    assert format_runner_label("") == "Playwright"


def test_format_run_status_text() -> None:
    assert "Успех" in format_run_status_text(True)
    assert "Ошибка" in format_run_status_text(False)


def test_format_failed_step_label() -> None:
    assert format_failed_step_label(None) == "—"
    assert format_failed_step_label(3) == "Шаг 3"


def test_summarize_run_history_empty() -> None:
    assert "не было" in summarize_run_history([])


def test_summarize_run_history_counts() -> None:
    entries = [
        RunHistoryEntry(True, "", "2026-06-22T10:00:00Z"),
        RunHistoryEntry(False, "boom", "2026-06-22T11:00:00Z"),
    ]
    text = summarize_run_history(entries)
    assert "2" in text
    assert "1" in text


def test_summarize_suite_cases() -> None:
    cases = [{"success": True}, {"success": False, "message": "x"}]
    text = summarize_suite_cases(cases)
    assert "2" in text
    assert "✗" in text


def test_format_single_run_summary() -> None:
    text = format_single_run_summary(
        {
            "success": False,
            "duration_ms": 1800,
            "runner": "playwright",
            "failed_step": 2,
            "message": "Timeout",
        }
    )
    assert "Ошибка" in text
    assert "Шаг 2" in text
    assert "1.8" in text
