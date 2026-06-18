"""Tests for playback journal formatting."""

from __future__ import annotations

from app.play_log import format_click_log, format_fill_generated_log, format_fill_log, step_log_target


def test_step_log_target_prefers_step_text() -> None:
    step = {
        "text": "Дата рождения *",
        "selector": 'label:has-text("Дата рождения *")',
    }
    assert step_log_target(step) == "Дата рождения"


def test_step_log_target_extracts_has_text() -> None:
    step = {"selector": 'button:has-text("Далее")'}
    assert step_log_target(step) == "Далее"


def test_format_fill_log_uses_field_name() -> None:
    step = {
        "text": "ИНН",
        "selector": 'label:has-text("ИНН")',
    }
    assert format_fill_log(5, step, "123") == '5. Ввод в «ИНН»: 123'


def test_format_fill_generated_log_uses_short_label() -> None:
    step = {
        "text": "Фамилия *",
        "selector": 'label:has-text("Фамилия *")',
        "generator": "last_name",
    }
    assert format_fill_generated_log(3, step, "last_name", "Попов") == "3. Фамилия: Попов"


def test_format_click_log_uses_button_text() -> None:
    step = {"selector": 'button:has-text("Далее")'}
    assert format_click_log(12, step) == '12. Клик «Далее»'
