"""Tests for Playwright export."""

from __future__ import annotations

from app.playwright_export import ExportFormat, export_scenario_playwright


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
