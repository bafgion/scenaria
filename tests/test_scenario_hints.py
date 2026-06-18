"""Tests for scenario quality hints."""

from __future__ import annotations

from app.scenario_hints import find_suspicious_menu_clicks, gherkin_template_text


def test_find_suspicious_menu_clicks() -> None:
    steps = [
        {"action": "goto", "url": "https://a.com"},
        {"action": "click", "selector": 'a:has-text("Платья")'},
        {"action": "hover", "selector": "nav"},
        {"action": "click", "selector": "a.item"},
        {"action": "click", "selector": "button.ok", "hoverSelector": "nav.menu"},
    ]
    assert find_suspicious_menu_clicks(steps) == [1]


def test_gherkin_template_contains_url() -> None:
    text = gherkin_template_text(url="https://store.test", scenario_name="Smoke")
    assert "https://store.test" in text
    assert "Сценарий: Smoke" in text
