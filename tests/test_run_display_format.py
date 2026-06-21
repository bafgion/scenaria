"""Tests for run display formatting."""

from __future__ import annotations

from app.run_display import format_last_run_summary, format_run_at


def test_format_run_at_shortens_iso() -> None:
    formatted = format_run_at("2026-06-17T14:30:00+00:00")
    assert "2026" in formatted
    assert "." in formatted
    assert ":" in formatted


def test_format_last_run_summary_includes_duration_and_step() -> None:
    text = format_last_run_summary(
        success=False,
        at="2026-06-17T14:30:00+00:00",
        duration_ms=12500,
        failed_step=3,
        message="timeout",
    )
    assert "ошибка" in text
    assert "12.5" in text or "мин" in text
    assert "шаг 3" in text
