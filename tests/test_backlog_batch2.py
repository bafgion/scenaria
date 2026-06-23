"""Backlog batch 2: A5-2 params, A7 tabs, A8-3 while/for_each."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from app.gherkin_ru import STEP_INDENT, gherkin_to_steps, steps_to_gherkin
from app.player import execute_step
from app.run_suite import expand_feature_cases
from app.run_variables import RunContext
from app.scenario_params import load_param_cases, param_case_count
from app.tab_helpers import resolve_tab_page

TAB = STEP_INDENT


def test_load_param_cases_from_list(tmp_path: Path) -> None:
    feature = tmp_path / "login.feature"
    feature.write_text(
        f"Сценарий: Login\n{TAB}Допустим открыт \"https://example.com\"\n",
        encoding="utf-8",
    )
    params = tmp_path / "login.params.json"
    params.write_text(
        json.dumps(
            [
                {"label": "admin", "variables": {"login": "admin@test.com"}},
                {"login": "user@test.com"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    cases = load_param_cases(feature)
    assert len(cases) == 2
    assert cases[0].label == "admin"
    assert cases[0].variables["login"] == "admin@test.com"
    assert cases[1].variables["login"] == "user@test.com"
    assert param_case_count(feature) == 2


def test_expand_feature_cases_with_params(tmp_path: Path) -> None:
    feature = tmp_path / "demo.feature"
    feature.write_text(
        f"Сценарий: Demo\n{TAB}Допустим открыт \"https://example.com\"\n",
        encoding="utf-8",
    )
    (tmp_path / "demo.params.json").write_text(
        json.dumps({"cases": [{"variables": {"role": "a"}}, {"variables": {"role": "b"}}]}),
        encoding="utf-8",
    )
    cases = expand_feature_cases(feature)
    assert len(cases) == 2
    assert cases[0].variables == {"role": "a"}
    assert cases[1].params_index == 2


def test_parse_tab_steps() -> None:
    text = (
        f"{TAB}Допустим открыт \"https://example.com\"\n"
        f'{TAB}И переключаюсь на вкладку "Оплата"\n'
        f'{TAB}И переключаюсь на вкладку с url "checkout"\n'
        f"{TAB}И переключаюсь на вкладку 2\n"
        f"{TAB}И переключаюсь на первую вкладку\n"
        f"{TAB}И переключаюсь на новую вкладку\n"
        f"{TAB}И закрываю текущую вкладку\n"
        f"{TAB}И проверяю что открыто 2 вкладки"
    )
    steps = gherkin_to_steps(text)
    assert steps[1] == {"action": "switch_tab", "mode": "title", "value": "Оплата"}
    assert steps[2]["mode"] == "url"
    assert steps[3] == {"action": "switch_tab", "mode": "index", "value": "1"}
    assert steps[4]["mode"] == "first"
    assert steps[5]["mode"] == "new"
    assert steps[6]["action"] == "close_tab"
    assert steps[7] == {"action": "assert_tab_count", "count": 2}


def test_resolve_tab_page_by_title() -> None:
    page_a = MagicMock()
    page_a.is_closed.return_value = False
    page_a.title.return_value = "Главная"
    page_b = MagicMock()
    page_b.is_closed.return_value = False
    page_b.title.return_value = "Оплата"
    context = MagicMock()
    context.pages = [page_a, page_b]
    assert resolve_tab_page(context, mode="title", value="оплат") is page_b


def test_resolve_tab_page_by_index() -> None:
    pages = []
    for title in ("A", "B", "C"):
        page = MagicMock()
        page.is_closed.return_value = False
        page.title.return_value = title
        pages.append(page)
    context = MagicMock()
    context.pages = pages
    assert resolve_tab_page(context, mode="index", value="0") is pages[0]
    assert resolve_tab_page(context, mode="index", value="2") is pages[2]
    assert resolve_tab_page(context, mode="index", value="9") is None


def test_roundtrip_switch_tab_index() -> None:
    steps = [{"action": "switch_tab", "mode": "index", "value": "1"}]
    text = steps_to_gherkin(steps, scenario_name="Tabs")
    reparsed = gherkin_to_steps(text)
    assert reparsed[0] == {"action": "switch_tab", "mode": "index", "value": "1"}
    assert "переключаюсь на вкладку 2" in text


def test_execute_switch_tab_updates_context() -> None:
    page_a = MagicMock()
    page_a.is_closed.return_value = False
    page_a.title.return_value = "A"
    page_b = MagicMock()
    page_b.is_closed.return_value = False
    page_b.title.return_value = "B"
    context = MagicMock()
    context.pages = [page_a, page_b]
    page_a.context = context

    ctx = RunContext()
    ctx.bind_page(page_a)
    step = {"action": "switch_tab", "mode": "title", "value": "B"}
    logs: list[str] = []
    execute_step(page_a, step, 1, logs.append, highlight=False, run_context=ctx)
    assert ctx.current_page(page_a) is page_b


def test_execute_assert_tab_count() -> None:
    page = MagicMock()
    page.is_closed.return_value = False
    page2 = MagicMock()
    page2.is_closed.return_value = False
    context = MagicMock()
    context.pages = [page, page2]
    page.context = context

    step = {"action": "assert_tab_count", "count": 2}
    execute_step(page, step, 1, lambda _msg: None, highlight=False, run_context=RunContext())


def test_parse_while_and_for_each_blocks() -> None:
    text = (
        f"{TAB}Пока url содержит \"/cart\"\n"
        f"{TAB}{TAB}И нажимаю \"button.plus\"\n"
        f'{TAB}Для каждого ".item" как "item"\n'
        f"{TAB}{TAB}И нажимаю \"button.buy\""
    )
    steps = gherkin_to_steps(text)
    assert steps[0]["action"] == "while"
    assert steps[0]["condition"]["type"] == "url_contains"
    assert steps[1]["action"] == "for_each"
    assert steps[1]["variable"] == "item"


def test_roundtrip_while_for_each() -> None:
    steps = [
        {
            "action": "while",
            "condition": {"type": "page_text", "value": "loading"},
            "steps": [{"action": "wait", "ms": 100}],
        },
        {
            "action": "for_each",
            "selector": ".row",
            "variable": "row",
            "steps": [{"action": "click", "selector": "button"}],
        },
    ]
    text = steps_to_gherkin(steps, scenario_name="Loops")
    reparsed = gherkin_to_steps(text)
    assert reparsed[0]["action"] == "while"
    assert reparsed[1]["action"] == "for_each"


def test_execute_for_each_remembers_items() -> None:
    locator_a = MagicMock()
    locator_a.inner_text.return_value = "Alpha"
    locator_b = MagicMock()
    locator_b.inner_text.return_value = "Beta"
    page = MagicMock()
    page.locator.return_value.all.return_value = [locator_a, locator_b]

    nested = {"action": "remember_text", "value": "{{item}}", "variable": "seen"}
    step = {
        "action": "for_each",
        "selector": ".item",
        "variable": "item",
        "steps": [nested],
    }
    ctx = RunContext()
    execute_step(page, step, 1, lambda _msg: None, highlight=False, run_context=ctx)
    assert ctx.get_variable("seen") == "Beta"
