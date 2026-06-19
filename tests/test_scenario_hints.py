"""Tests for scenario quality hints."""

from __future__ import annotations

from app.scenario_hints import (
    apply_menu_hover_fix_at_index,
    find_suspicious_menu_clicks,
    gherkin_template_text,
    propose_menu_hover_fix,
    split_playwright_chain_selector,
)


def test_split_playwright_chain_selector() -> None:
    selector = 'div:has-text("Вязаный трикотаж") >> button:has-text("Толстовки")'
    assert split_playwright_chain_selector(selector) == (
        'div:has-text("Вязаный трикотаж")',
        'button:has-text("Толстовки")',
    )


def test_propose_menu_hover_fix_from_chain() -> None:
    step = {
        "action": "click",
        "selector": 'div:has-text("Категория") >> button:has-text("Товар")',
    }
    assert propose_menu_hover_fix(step) == (
        'div:has-text("Категория") >> a:has-text("Категория")',
        'button:has-text("Товар")',
    )


def test_apply_menu_hover_fix_splits_click_step() -> None:
    steps = [
        {"action": "goto", "url": "https://a.com"},
        {
            "action": "click",
            "selector": 'div:has-text("Категория") >> button:has-text("Товар")',
        },
    ]
    updated = apply_menu_hover_fix_at_index(steps, 1)
    assert updated is not None
    assert updated[1] == {
        "action": "hover",
        "selector": 'div:has-text("Категория") >> a:has-text("Категория")',
    }
    assert updated[2]["action"] == "click"
    assert updated[2]["selector"] == 'button:has-text("Товар")'
    assert updated[2]["hoverSelector"] == 'div:has-text("Категория") >> a:has-text("Категория")'


def test_find_suspicious_menu_clicks() -> None:
    steps = [
        {"action": "goto", "url": "https://a.com"},
        {"action": "click", "selector": 'a:has-text("Платья")'},
        {"action": "hover", "selector": "nav"},
        {"action": "click", "selector": "a.item"},
        {"action": "click", "selector": "button.ok", "hoverSelector": "nav.menu"},
        {
            "action": "click",
            "selector": 'div:has-text("Меню") >> button:has-text("Пункт")',
        },
    ]
    assert find_suspicious_menu_clicks(steps) == [1, 5]


def test_gherkin_template_contains_url() -> None:
    text = gherkin_template_text(url="https://store.test", scenario_name="Smoke")
    assert "https://store.test" in text
    assert "Сценарий: Smoke" in text
