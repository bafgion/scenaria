"""Tests for scenario variables and remember steps."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.gherkin_ru import gherkin_to_steps, parse_gherkin_steps, steps_to_gherkin
from app.player import execute_step
from app.run_variables import RunContext


def test_resolve_user_variable() -> None:
    ctx = RunContext()
    ctx.remember("login", "user@example.com")
    assert ctx.resolve_text('ввожу "{{login}}" в поле') == 'ввожу "user@example.com" в поле'


def test_resolve_env_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCENARIA_TEST_VAR", "secret")
    ctx = RunContext()
    assert ctx.resolve_text("{{env:SCENARIA_TEST_VAR}}") == "secret"


def test_unknown_variable_raises() -> None:
    ctx = RunContext()
    with pytest.raises(ValueError, match="Неизвестная переменная"):
        ctx.resolve_text("{{missing}}")


def test_remember_text_round_trip() -> None:
    text = (
        'Функционал: Vars\n'
        'Сценарий: S\n'
        '\tИ запоминаю текст "alpha" как "name"\n'
        '\tИ ввожу "{{name}}" в "input"\n'
    )
    steps, _ = parse_gherkin_steps(text)
    assert steps[0]["action"] == "remember_text"
    assert steps[1]["action"] == "fill"
    restored = steps_to_gherkin(steps, scenario_name="S")
    assert "запоминаю текст" in restored


def test_execute_fill_with_variable() -> None:
    page = MagicMock()
    page.url = "https://example.com"
    locator = MagicMock()
    page.locator.return_value = locator
    locator.first = locator

    ctx = RunContext()
    ctx.remember("login", "user@test.com")
    logs: list[str] = []
    execute_step(
        page,
        {"action": "fill", "selector": "#email", "value": "{{login}}"},
        1,
        logs.append,
        highlight=False,
        run_context=ctx,
    )
    locator.fill.assert_called_once()
    assert locator.fill.call_args[0][0] == "user@test.com"


def test_execute_remember_url() -> None:
    page = MagicMock()
    page.url = "https://example.com/profile"
    ctx = RunContext()
    logs: list[str] = []
    execute_step(
        page,
        {"action": "remember_url", "variable": "profile_url"},
        1,
        logs.append,
        highlight=False,
        run_context=ctx,
    )
    assert ctx.get_variable("profile_url") == "https://example.com/profile"


def test_gherkin_to_steps_download() -> None:
    text = 'Функционал: D\nСценарий: S\n\tИ скачиваю по клику на "a.export"\n'
    steps = gherkin_to_steps(text)
    assert steps[-1]["action"] == "download_click"
