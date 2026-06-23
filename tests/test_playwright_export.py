"""Tests for Playwright export."""

from __future__ import annotations

import pytest

from app.playwright_export import (
    ExportFormat,
    ExportSupport,
    EXPORT_ACTION_SUPPORT,
    analyze_export,
    export_scenario_playwright,
    export_support_for_action,
)


def test_export_typescript_includes_steps() -> None:
    scenario = {
        "name": "Checkout",
        "steps": [
            {"action": "goto", "url": "https://shop.com"},
            {"action": "click", "selector": "button.buy"},
            {"action": "assert_visible", "selector": "h1.done"},
            {"action": "assert_text", "value": "Спасибо", "selector": ".msg"},
            {"action": "assert_url", "url": "https://shop.com/thanks"},
        ],
    }
    text = export_scenario_playwright(scenario, fmt=ExportFormat.TYPESCRIPT)
    assert "import { test, expect }" in text
    assert 'test("Checkout"' in text
    assert "page.goto" in text
    assert "button.buy" in text
    assert "toBeVisible" in text
    assert "toContainText" in text
    assert "toHaveURL" in text


def test_export_python_includes_steps() -> None:
    scenario = {
        "name": "Login",
        "steps": [
            {"action": "goto", "url": "https://shop.com/login"},
            {"action": "fill", "value": "user@test.com", "selector": "#email"},
            {"action": "hover", "selector": "nav.menu"},
        ],
    }
    text = export_scenario_playwright(scenario, fmt=ExportFormat.PYTHON)
    assert "def test_Login" in text
    assert "page.goto" in text
    assert "fill(" in text
    assert ".hover()" in text


def test_export_extended_steps() -> None:
    scenario = {
        "name": "Universal",
        "steps": [
            {"action": "press", "key": "Enter"},
            {"action": "scroll_to", "selector": "#footer"},
            {"action": "assert_hidden", "selector": ".modal"},
            {"action": "reload"},
            {"action": "wait_for_hidden", "selector": ".spinner"},
        ],
    }
    ts = export_scenario_playwright(scenario, fmt=ExportFormat.TYPESCRIPT)
    assert "keyboard.press" in ts
    assert "scrollIntoViewIfNeeded" in ts
    assert "toBeHidden" in ts
    assert "page.reload" in ts
    assert "state: 'hidden'" in ts

    py = export_scenario_playwright(scenario, fmt=ExportFormat.PYTHON)
    assert "keyboard.press" in py
    assert "scroll_into_view_if_needed" in py
    assert "to_be_hidden" in py
    assert "page.reload" in py


@pytest.mark.parametrize(
    ("action", "step", "needles"),
    [
        ("goto", {"action": "goto", "url": "https://x"}, ["page.goto"]),
        ("go_back", {"action": "go_back"}, ["goBack", "go_back"]),
        ("reload", {"action": "reload"}, ["reload"]),
        ("scroll_to", {"action": "scroll_to", "selector": "#x"}, ["scroll"]),
        ("click", {"action": "click", "selector": "button"}, [".click()"]),
        ("double_click", {"action": "double_click", "selector": "button"}, ["dblclick"]),
        ("hover", {"action": "hover", "selector": "nav"}, [".hover()"]),
        ("fill", {"action": "fill", "selector": "#e", "value": "a"}, [".fill("]),
        ("clear", {"action": "clear", "selector": "#e"}, [".clear()"]),
        ("select", {"action": "select", "selector": "select", "value": "1"}, ["select"]),
        ("check", {"action": "check", "selector": "input"}, [".check()"]),
        ("uncheck", {"action": "uncheck", "selector": "input"}, [".uncheck()"]),
        ("press", {"action": "press", "key": "Tab"}, ["keyboard.press"]),
        ("upload", {"action": "upload", "selector": "input", "path": "f.pdf"}, ["setInputFiles", "set_input_files"]),
        ("draw_signature", {"action": "draw_signature", "selector": "canvas"}, ["mouse.down"]),
        ("assert_visible", {"action": "assert_visible", "selector": ".x"}, ["toBeVisible", "to_be_visible"]),
        ("assert_hidden", {"action": "assert_hidden", "selector": ".x"}, ["toBeHidden", "to_be_hidden"]),
        ("assert_text", {"action": "assert_text", "selector": ".x", "value": "ok"}, ["toContainText", "to_contain_text"]),
        ("assert_url", {"action": "assert_url", "url": "https://x"}, ["toHaveURL", "to_have_url"]),
        ("wait", {"action": "wait", "ms": 500}, ["waitForTimeout", "wait_for_timeout"]),
        ("wait_for", {"action": "wait_for", "selector": ".x"}, ["waitFor", "wait_for"]),
        ("wait_for_hidden", {"action": "wait_for_hidden", "selector": ".x"}, ["hidden"]),
        ("close_browser", {"action": "close_browser"}, ["close"]),
    ],
)
def test_supported_action_exports(action: str, step: dict, needles: list[str]) -> None:
    assert export_support_for_action(action) == ExportSupport.SUPPORTED
    scenario = {"name": action, "steps": [step]}
    ts = export_scenario_playwright(scenario, fmt=ExportFormat.TYPESCRIPT)
    py = export_scenario_playwright(scenario, fmt=ExportFormat.PYTHON)
    assert "unsupported action" not in ts
    assert "unsupported action" not in py
    assert any(needle in ts or needle in py for needle in needles)


def test_fill_generated_is_partial_not_todo() -> None:
    scenario = {
        "name": "Gen",
        "steps": [{"action": "fill_generated", "generator": "phone", "selector": "input"}],
    }
    assert export_support_for_action("fill_generated") == ExportSupport.PARTIAL
    ts = export_scenario_playwright(scenario, fmt=ExportFormat.TYPESCRIPT)
    py = export_scenario_playwright(scenario, fmt=ExportFormat.PYTHON)
    assert "TODO: generate" not in ts
    assert "TODO: generate" not in py
    assert "partial export" in ts
    assert "SCENARIA_GEN_PHONE" in ts
    assert "import os" in py
    assert "partial export" in py


@pytest.mark.parametrize(
    "action",
    [
        "if",
        "repeat",
        "while",
        "for_each",
        "switch_tab",
        "download_click",
        "remember_text",
        "prompt_email_code",
    ],
)
def test_unsupported_action_gets_comment(action: str) -> None:
    assert export_support_for_action(action) == ExportSupport.UNSUPPORTED
    scenario = {"name": "X", "steps": [{"action": action}]}
    ts = export_scenario_playwright(scenario, fmt=ExportFormat.TYPESCRIPT)
    assert f"unsupported action: {action}" in ts
    assert "unsupported:" in ts


def test_analyze_export_groups_actions() -> None:
    scenario = {
        "name": "Mix",
        "steps": [
            {"action": "goto", "url": "https://x"},
            {"action": "click", "selector": "a"},
            {"action": "fill_generated", "generator": "phone", "selector": "input"},
            {"action": "if", "condition": "visible", "selector": ".x", "steps": []},
        ],
    }
    analysis = analyze_export(scenario)
    assert analysis.supported == ["goto", "click"]
    assert analysis.partial == ["fill_generated"]
    assert analysis.unsupported == ["if"]
    assert analysis.has_blocking_issues
    assert analysis.has_warnings


def test_catalog_actions_have_export_support_entry() -> None:
    from app.step_catalog import CATALOG

    catalog_actions = {entry.action for entry in CATALOG if entry.action}
    catalog_actions.add("draw_signature")
    missing = catalog_actions - set(EXPORT_ACTION_SUPPORT)
    assert not missing, f"missing export mapping: {sorted(missing)}"
