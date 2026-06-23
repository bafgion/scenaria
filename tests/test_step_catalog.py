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


def test_list_step_entries_conditions_and_loops() -> None:
    conditions = list_step_entries(category="conditions")
    loops = list_step_entries(category="loops")
    assert any(entry.action == "if" for entry in conditions)
    assert any(entry.label.startswith("если") for entry in conditions)
    assert any(entry.action == "repeat" for entry in loops)
    assert any(entry.action == "while" for entry in loops)
    assert any(entry.action == "for_each" for entry in loops)


def test_catalog_includes_remember_field() -> None:
    matches = list_step_entries(query="запоминаю значение поля")
    assert matches
    assert matches[0].action == "remember_field"


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


def test_catalog_includes_tab_steps() -> None:
    tabs = list_step_entries(category="tabs")
    actions = {entry.action for entry in tabs}
    assert "switch_tab" in actions
    assert "close_tab" in actions
    assert "assert_tab_count" in actions
    titles = {entry.label for entry in tabs}
    assert "переключаюсь на вкладку" in titles
    assert "переключаюсь на вкладку с url" in titles
    assert "закрываю текущую вкладку" in titles


def test_resolve_tab_switch_by_title() -> None:
    line = '\tИ переключаюсь на вкладку "Оплата"'
    entry = resolve_step_entry(line=line)
    assert entry is not None
    assert entry.action == "switch_tab"
    assert "Оплата" in entry.example


def test_resolve_tab_switch_by_url() -> None:
    line = '\tИ переключаюсь на вкладку с url "checkout"'
    entry = resolve_step_entry(line=line)
    assert entry is not None
    assert entry.action == "switch_tab"
    assert "checkout" in entry.example


def test_all_parser_actions_have_catalog_entry() -> None:
    """Every action emitted by gherkin_ru parser should appear in step help."""
    expected_actions = {
        "goto",
        "go_back",
        "reload",
        "scroll_to",
        "click",
        "double_click",
        "hover",
        "fill",
        "fill_generated",
        "clear",
        "select",
        "check",
        "uncheck",
        "press",
        "prompt_email_code",
        "upload",
        "download_click",
        "assert_download_contains",
        "remember_text",
        "remember_field",
        "remember_url",
        "draw_signature",
        "assert_visible",
        "assert_hidden",
        "assert_text",
        "assert_url",
        "wait",
        "wait_for",
        "wait_for_hidden",
        "close_browser",
        "switch_tab",
        "close_tab",
        "assert_tab_count",
        "if",
        "repeat",
        "while",
        "for_each",
    }
    catalog_actions = {entry.action for entry in CATALOG if entry.action}
    missing = expected_actions - catalog_actions
    assert not missing, f"Missing catalog entries for actions: {sorted(missing)}"
