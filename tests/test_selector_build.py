"""Tests for smart selector strategy."""

from __future__ import annotations

from app.scenario_hints import collect_all_hints, find_fragile_selector_indices
from app.selector_build import (
    apply_smart_selector_to_step,
    build_selector_from_info,
    is_fragile_selector,
)


def test_prefers_testid_over_css_path() -> None:
    info = {
        "tag": "button",
        "testId": "checkout",
        "text": "Оформить",
        "fallbackSelector": "div > button:nth-of-type(2)",
    }
    choice = build_selector_from_info(info)
    assert choice.strategy == "testid"
    assert choice.selector == '[data-testid="checkout"]'
    assert choice.fragile is False


def test_skips_auto_generated_react_id() -> None:
    info = {
        "tag": "button",
        "id": "react-select-3-input",
        "text": "OK",
        "fallbackSelector": "div > button:nth-of-type(1)",
    }
    choice = build_selector_from_info(info)
    assert choice.strategy != "id"
    assert choice.selector != "#react-select-3-input"


def test_input_prefers_label_text_over_nth_of_type() -> None:
    info = {
        "tag": "input",
        "inputType": "email",
        "captionText": "E-mail",
        "fallbackSelector": "label:nth-of-type(1) > div:nth-of-type(2) > input",
    }
    choice = build_selector_from_info(info)
    assert choice.strategy == "text"
    assert choice.selector.startswith('label:has-text("')


def test_chain_selector_when_context_available() -> None:
    info = {
        "tag": "button",
        "text": "Выбрать",
        "contextText": "Договор с самозанятым",
        "fallbackSelector": "button.btn",
    }
    choice = build_selector_from_info(
        info,
        priority=["chain", "text", "css"],
    )
    assert choice.strategy == "chain"
    assert " >> " in choice.selector


def test_apply_smart_selector_strips_element_info() -> None:
    step = apply_smart_selector_to_step(
        {
            "action": "click",
            "selector": "div > button:nth-of-type(1)",
            "elementInfo": {
                "tag": "button",
                "testId": "save",
                "text": "Save",
                "fallbackSelector": "div > button:nth-of-type(1)",
            },
        }
    )
    assert "elementInfo" not in step
    assert step["selector"] == '[data-testid="save"]'
    assert step["selectorStrategy"] == "testid"
    assert step["fragile"] is False


def test_is_fragile_selector_detects_nth_of_type() -> None:
    assert is_fragile_selector("div > label:nth-of-type(1) > input")
    assert not is_fragile_selector('[data-testid="x"]')


def test_fragile_selector_hint() -> None:
    steps = [
        {"action": "click", "selector": "div > button:nth-of-type(2)", "fragile": True},
    ]
    assert find_fragile_selector_indices(steps) == [0]
    hints = collect_all_hints(steps)
    assert any(hint.id == "fragile_selector" for hint in hints)
