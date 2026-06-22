"""Sprint 6c: A8 conditions/loops, A9 outline, E2 quick fixes, C5 parallel batch."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.gherkin_quick_fixes import suggest_quick_fixes, suggest_quick_fixes_for_error, suggest_quick_fixes_for_error
from app.gherkin_ru import STEP_INDENT, gherkin_to_steps, steps_to_gherkin
from app.gherkin_outline import expand_outline_steps, outline_example_count, parse_outline, substitute_outline_value
from app.player import _evaluate_condition, execute_step
from app.run_suite import collect_run_cases, expand_feature_cases
from app.run_variables import RunContext

TAB = STEP_INDENT


def test_parse_if_block() -> None:
    text = (
        "Сценарий: Cookie\n"
        f"{TAB}Допустим открыт \"https://shop.com\"\n"
        f"{TAB}Если вижу \".cookie-banner\"\n"
        f"{TAB}{TAB}И нажимаю \"button.accept\""
    )
    steps = gherkin_to_steps(text)
    assert steps[1]["action"] == "if"
    assert steps[1]["condition"]["type"] == "visible"
    assert steps[1]["steps"][0]["action"] == "click"


def test_parse_repeat_block() -> None:
    text = (
        f"{TAB}Повторяю 3 раза\n"
        f"{TAB}{TAB}И нажимаю \"button.add\""
    )
    steps = gherkin_to_steps(text)
    assert steps[0]["action"] == "repeat"
    assert steps[0]["count"] == 3
    assert steps[0]["steps"][0]["selector"] == "button.add"


def test_roundtrip_if_repeat() -> None:
    steps = [
        {
            "action": "if",
            "condition": {"type": "url_contains", "value": "/cart"},
            "steps": [{"action": "click", "selector": "button.checkout"}],
        },
        {
            "action": "repeat",
            "count": 2,
            "steps": [{"action": "click", "selector": "button.plus"}],
        },
    ]
    text = steps_to_gherkin(steps, scenario_name="Blocks")
    reparsed = gherkin_to_steps(text)
    assert reparsed[0]["action"] == "if"
    assert reparsed[1]["action"] == "repeat"


def test_execute_if_skips_nested_steps() -> None:
    page = MagicMock()
    page.url = "https://example.com"
    page.locator.return_value.first.is_visible.return_value = False
    page.content.return_value = ""

    nested = {"action": "click", "selector": "#never"}
    step = {
        "action": "if",
        "condition": {"type": "visible", "selector": "#banner"},
        "steps": [nested],
    }
    logs: list[str] = []
    execute_step(page, step, 1, logs.append, highlight=False, run_context=RunContext())
    assert any("пропуск" in line.lower() for line in logs)


def test_evaluate_condition_page_text() -> None:
    page = MagicMock()
    page.content.return_value = "Добро пожаловать"
    ctx = RunContext()
    assert _evaluate_condition(page, {"type": "page_text", "value": "пожаловать"}, ctx)


def test_parse_outline_and_expand() -> None:
    text = (
        "Функционал: Auth\n"
        "Структура сценария: Вход\n"
        f'{TAB}Допустим открыт "<url>"\n'
        f'{TAB}И ввожу "<login>" в "#email"\n'
        "\n"
        "Примеры:\n"
        "  | url              | login   |\n"
        "  | https://a.com    | a@test  |\n"
        "  | https://b.com    | b@test  |"
    )
    outline = parse_outline(text)
    assert outline is not None
    assert len(outline.rows) == 2
    assert outline_example_count(text) == 2
    expanded = expand_outline_steps(outline.template_steps, outline.rows[0])
    assert expanded[0]["url"] == "https://a.com"
    assert expanded[1]["value"] == "a@test"
    assert substitute_outline_value("open <url>", {"url": "https://x"}) == "open https://x"


def test_expand_feature_cases(tmp_path: Path) -> None:
    feature = tmp_path / "login.feature"
    feature.write_text(
        (
            "Структура сценария: Login\n"
            f'{TAB}Допустим открыт "<url>"\n'
            "Примеры:\n"
            "  | url |\n"
            "  | https://one |\n"
            "  | https://two |"
        ),
        encoding="utf-8",
    )
    cases = expand_feature_cases(feature)
    assert len(cases) == 2
    assert cases[0].steps[0]["url"] == "https://one"
    assert cases[1].steps[0]["url"] == "https://two"


def test_collect_run_cases_expands_outline(tmp_path: Path) -> None:
    feature = tmp_path / "data.feature"
    feature.write_text(
        (
            "Структура сценария: Data\n"
            f'{TAB}Допустим открыт "<url>"\n'
            "Примеры:\n"
            "  | url |\n"
            "  | https://a |\n"
        ),
        encoding="utf-8",
    )
    cases = collect_run_cases([feature])
    assert len(cases) == 1
    assert cases[0].steps[0]["url"] == "https://a"


def test_quick_fix_typo_and_indent() -> None:
    text = "  Дапустим открыт \"https://a.com\""
    fixes = suggest_quick_fixes(text, 1)
    labels = [item[0].label for item in fixes]
    assert any("Допустим" in label for label in labels)
    assert any("таб" in label for label in labels)


def test_quick_fix_missing_quote() -> None:
    text = f"{TAB}И нажимаю \"button"
    fixes = suggest_quick_fixes(text, 1)
    assert fixes
    assert fixes[0][1].endswith('"')


def test_quick_fix_whole_file_indents() -> None:
    text = (
        "Сценарий: T\n"
        f"{TAB}Допустим открыт \"https://a.com\"\n"
        f'    И нажимаю "#id"\n'
    )
    fixes = suggest_quick_fixes_for_error(text, 3)
    labels = [item[0].label for item in fixes]
    assert "Исправить отступы во всём файле" in labels
    whole = next(item[1] for item in fixes if item[0].label == "Исправить отступы во всём файле")
    assert '    И нажимаю' not in whole
