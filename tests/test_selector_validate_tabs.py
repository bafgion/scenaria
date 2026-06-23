"""Selector validation for tab steps (A7-1)."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.selector_validate import validate_scenario_selectors, validate_step_selector


def _page_with_tabs(count: int) -> MagicMock:
    pages = []
    for index in range(count):
        page = MagicMock()
        page.is_closed.return_value = False
        page.title.return_value = f"Tab {index + 1}"
        page.url = f"https://example.com/{index + 1}"
        pages.append(page)
    context = MagicMock()
    context.pages = pages
    root = pages[0]
    root.context = context
    return root


def test_validate_switch_tab_by_title_ok() -> None:
    page = _page_with_tabs(2)
    results = validate_scenario_selectors(
        page,
        {"steps": [{"action": "switch_tab", "mode": "title", "value": "Tab 2"}]},
    )
    assert len(results) == 1
    assert results[0].status == "ok"


def test_validate_switch_tab_not_found() -> None:
    page = _page_with_tabs(1)
    results = validate_scenario_selectors(
        page,
        {"steps": [{"action": "switch_tab", "mode": "title", "value": "Missing"}]},
    )
    assert results[0].status == "error"
    assert "не найдена" in results[0].message


def test_validate_switch_tab_by_index() -> None:
    page = _page_with_tabs(3)
    results = validate_scenario_selectors(
        page,
        {"steps": [{"action": "switch_tab", "mode": "index", "value": "2"}]},
    )
    assert results[0].status == "ok"


def test_validate_close_tab_requires_more_than_one() -> None:
    page = _page_with_tabs(1)
    result = validate_step_selector(page, {"action": "close_tab"}, step_index=1)
    assert result is not None
    assert result.status == "error"


def test_validate_close_tab_ok() -> None:
    page = _page_with_tabs(2)
    result = validate_step_selector(page, {"action": "close_tab"}, step_index=1)
    assert result is not None
    assert result.status == "ok"


def test_validate_assert_tab_count() -> None:
    page = _page_with_tabs(2)
    results = validate_scenario_selectors(
        page,
        {"steps": [{"action": "assert_tab_count", "count": 2}]},
    )
    assert results[0].status == "ok"

    mismatch = validate_scenario_selectors(
        page,
        {"steps": [{"action": "assert_tab_count", "count": 3}]},
    )
    assert mismatch[0].status == "error"
    assert "открыто 2" in mismatch[0].message
