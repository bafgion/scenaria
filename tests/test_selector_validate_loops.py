"""Selector validation for while / for_each blocks."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.selector_validate import validate_scenario_selectors, validate_step_selector


def test_validate_step_selector_skips_loop_blocks() -> None:
    page = MagicMock()
    for action in ("while", "for_each"):
        result = validate_step_selector(page, {"action": action}, step_index=1)
        assert result is not None
        assert result.status == "skipped"
        assert result.action == action


def test_validate_for_each_checks_list_selector() -> None:
    page = MagicMock()
    page.url = "https://example.com"
    page.locator.return_value.count.return_value = 0

    results = validate_scenario_selectors(
        page,
        {
            "steps": [
                {
                    "action": "for_each",
                    "selector": ".missing",
                    "variable": "item",
                    "steps": [],
                }
            ]
        },
    )
    assert len(results) == 1
    assert results[0].action == "for_each"
    assert results[0].status == "not_found"


def test_validate_for_each_allows_multiple_elements() -> None:
    page = MagicMock()
    page.url = "https://example.com"
    page.locator.return_value.count.return_value = 5

    results = validate_scenario_selectors(
        page,
        {
            "steps": [
                {
                    "action": "for_each",
                    "selector": ".item",
                    "variable": "item",
                    "steps": [],
                }
            ]
        },
    )
    assert len(results) == 1
    assert results[0].status == "ok"


def test_validate_for_each_recurses_into_nested_steps() -> None:
    page = MagicMock()
    page.url = "https://example.com"
    page.locator.return_value.count.return_value = 2

    with patch("app.selector_validate._locator_issues", return_value=["элемент не найден"]):
        results = validate_scenario_selectors(
            page,
            {
                "steps": [
                    {
                        "action": "for_each",
                        "selector": ".item",
                        "variable": "item",
                        "steps": [{"action": "click", "selector": "button.buy"}],
                    }
                ]
            },
        )

    actions = {item.action: item for item in results}
    assert actions["for_each"].status == "ok"
    assert actions["click"].status == "not_found"
    assert actions["click"].selector == "button.buy"


def test_validate_while_checks_url_condition() -> None:
    page = MagicMock()
    page.url = "https://example.com/cart"

    results = validate_scenario_selectors(
        page,
        {
            "steps": [
                {
                    "action": "while",
                    "condition": {"type": "url_contains", "value": "/cart"},
                    "steps": [],
                }
            ]
        },
    )
    assert len(results) == 1
    assert results[0].action == "while_condition"
    assert results[0].status == "ok"


def test_validate_while_url_condition_error() -> None:
    page = MagicMock()
    page.url = "https://example.com/home"

    results = validate_scenario_selectors(
        page,
        {
            "steps": [
                {
                    "action": "while",
                    "condition": {"type": "url_contains", "value": "/cart"},
                    "steps": [],
                }
            ]
        },
    )
    assert results[0].status == "error"


def test_validate_while_visible_condition_and_nested() -> None:
    page = MagicMock()
    page.url = "https://example.com"

    with patch("app.selector_validate._locator_issues", return_value=[]) as locator_issues:
        results = validate_scenario_selectors(
            page,
            {
                "steps": [
                    {
                        "action": "while",
                        "condition": {"type": "visible", "selector": ".loader"},
                        "steps": [{"action": "click", "selector": "button.ok"}],
                    }
                ]
            },
        )

    assert any(call.args[1] == ".loader" for call in locator_issues.call_args_list)
    actions = {item.action: item for item in results}
    assert actions["while_condition"].status == "ok"
    assert actions["click"].status == "ok"
