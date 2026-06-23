"""Tests for Gherkin Контекст / TestClient."""

from __future__ import annotations

import pytest

from app.gherkin_context import format_context_lines, parse_feature_test_client
from app.gherkin_ru import STEP_INDENT, GherkinParseError, gherkin_to_steps, parse_feature_structure


def test_parse_context_test_client() -> None:
    text = (
        "Функционал: Заказы\n"
        "Контекст:\n"
        f'{STEP_INDENT}Дано я подключаю TestClient "ВолковаА_ГК"\n'
        "Сценарий: Создание\n"
        f'{STEP_INDENT}Допустим открыт "https://example.com"\n'
    )
    assert parse_feature_test_client(text) == "ВолковаА_ГК"
    steps = gherkin_to_steps(text)
    assert steps[0]["action"] == "goto"
    structure = parse_feature_structure(text)
    assert structure.has_context_block is True


def test_no_context_means_clean_session() -> None:
    text = (
        "Функционал: Demo\n"
        "Сценарий: Open\n"
        f'{STEP_INDENT}Допустим открыт "https://example.com"\n'
    )
    assert parse_feature_test_client(text) is None


def test_context_steps_not_in_scenario_steps() -> None:
    text = (
        "Функционал: Demo\n"
        "Контекст:\n"
        f'{STEP_INDENT}Дано я подключаю TestClient "User1"\n'
        "Сценарий: Open\n"
        f'{STEP_INDENT}Допустим открыт "https://example.com"\n'
    )
    steps = gherkin_to_steps(text)
    assert len(steps) == 1
    assert steps[0]["action"] == "goto"


def test_multiple_test_clients_in_context_error() -> None:
    text = (
        "Контекст:\n"
        f'{STEP_INDENT}Дано я подключаю TestClient "A"\n'
        f"{STEP_INDENT}И я подключаю TestClient \"B\"\n"
    )
    with pytest.raises(GherkinParseError, match="только один"):
        parse_feature_test_client(text)


def test_format_context_lines_roundtrip_name() -> None:
    lines = format_context_lines("ВолковаА_ГК")
    text = "Функционал: X\n" + "\n".join(lines) + "\nСценарий: Y\n\tДопустим открыт \"https://x.com\"\n"
    assert parse_feature_test_client(text) == "ВолковаА_ГК"
