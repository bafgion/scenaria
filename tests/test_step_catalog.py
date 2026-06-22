"""Tests for step catalog and line resolution."""

from __future__ import annotations

from app.step_catalog import (
    CATEGORY_LABELS,
    CATALOG,
    entry_for_action,
    list_step_entries,
    resolve_step_entry,
)


def test_catalog_covers_all_step_snippets() -> None:
    assert len(CATALOG) >= 20


def test_list_step_entries_filter_category() -> None:
    navigation = list_step_entries(category="navigation")
    assert navigation
    assert all(entry.category == "navigation" for entry in navigation)
    assert any(entry.action == "goto" for entry in navigation)


def test_list_step_entries_search() -> None:
    matches = list_step_entries(query="нажимаю")
    assert any(entry.label == "нажимаю" for entry in matches)


def test_resolve_step_entry_from_goto_line() -> None:
    text = 'Функционал: X\n\tДопустим открыт "https://example.com"'
    entry = resolve_step_entry(text=text, line_no=2)
    assert entry is not None
    assert entry.action == "goto"


def test_resolve_step_entry_from_click_line() -> None:
    line = '\tИ нажимаю "button.submit"'
    entry = resolve_step_entry(line=line)
    assert entry is not None
    assert entry.action == "click"


def test_entry_for_action_fill_generated_disambiguation() -> None:
    phone = entry_for_action("fill_generated", line_body='ввожу случайный телефон в "input"')
    assert phone is not None
    assert "телефон" in phone.label


def test_format_entry_help_structured_html() -> None:
    from app.step_catalog import format_entry_help

    entry = entry_for_action("goto")
    assert entry is not None
    html_text = format_entry_help(entry)
    assert "открыт" in html_text
    assert "goto" in html_text
    assert "Навигация" in html_text
    assert "https://" in html_text
    assert "param-line" in html_text
    assert "example-box" in html_text


def test_category_labels_complete() -> None:
    categories = {entry.category for entry in CATALOG}
    for category in categories:
        assert category in CATEGORY_LABELS
