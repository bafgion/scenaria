"""Tests for find/replace helpers."""

from __future__ import annotations

from app.text_replace import find_matches, line_is_replaceable, replace_all


SAMPLE = """Функционал: UI
@smoke
Сценарий: Demo
\t# old url
\tДопустим открыт "https://staging.example.com"
\tИ нажимаю "buy"
"""


def test_line_is_replaceable_skips_headers_tags_comments() -> None:
    assert not line_is_replaceable("Функционал: UI", steps_only=True)
    assert not line_is_replaceable("@smoke", steps_only=True)
    assert not line_is_replaceable("\t# note", steps_only=True)
    assert line_is_replaceable('\tДопустим открыт "x"', steps_only=True)


def test_find_matches_respects_steps_only() -> None:
    all_matches = find_matches(SAMPLE, "example", steps_only=False)
    step_matches = find_matches(SAMPLE, "example", steps_only=True)
    assert len(all_matches) >= len(step_matches)
    assert len(step_matches) == 1


def test_replace_all_in_steps_only() -> None:
    updated, count = replace_all(
        SAMPLE,
        "staging.example.com",
        "prod.example.com",
        steps_only=True,
    )
    assert count == 1
    assert "staging" not in updated
    assert "@smoke" in updated
    assert "Функционал: UI" in updated


def test_replace_all_preserves_indents() -> None:
    updated, count = replace_all(
        SAMPLE,
        "buy",
        "checkout",
        steps_only=True,
    )
    assert count == 1
    assert '\tИ нажимаю "checkout"' in updated
