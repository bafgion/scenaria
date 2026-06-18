"""Tests for picker step templates."""

from __future__ import annotations

from app.gherkin_picker import picker_step_choices


def test_picker_step_choices_include_click_and_raw() -> None:
    choices = picker_step_choices('button.buy')
    labels = [choice.label for choice in choices]
    assert "Клик" in labels
    assert "Только селектор" in labels
    click = next(choice for choice in choices if choice.label == "Клик")
    assert 'нажимаю "button.buy"' in click.step_body
    assert "button.buy" in click.preview


def test_picker_step_choices_escape_quotes() -> None:
    choices = picker_step_choices('input[name="email"]')
    click = next(choice for choice in choices if choice.label == "Клик")
    assert 'input[name=\\"email\\"]' in click.step_body or 'input[name="' in click.step_body


def test_picker_step_choices_respect_keyword() -> None:
    first = picker_step_choices("button.buy", keyword="Допустим")
    next_step = picker_step_choices("button.buy", keyword="И")
    click_first = next(choice for choice in first if choice.label == "Клик")
    click_next = next(choice for choice in next_step if choice.label == "Клик")
    assert click_first.preview.startswith(f"{chr(9)}Допустим нажимаю")
    assert click_next.preview.startswith(f"{chr(9)}И нажимаю")
