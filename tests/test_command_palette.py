"""Command palette filter tests."""

from __future__ import annotations

from app.qt.widgets.command_palette import PaletteCommand, filter_commands, match_score


def _cmd(label: str) -> PaletteCommand:
    return PaletteCommand(id=label.lower(), label=label, shortcut="", run=lambda: None)


def test_match_score_substring() -> None:
    assert match_score("запуск", "Запустить") is not None
    assert match_score("zzz", "Запустить") is None


def test_filter_commands_finds_run_variants() -> None:
    commands = [
        _cmd("Запустить"),
        _cmd("Запустить выбранные"),
        _cmd("Пакетный запуск (Vanessa Automation)…"),
        _cmd("Сохранить"),
    ]
    matches = filter_commands("запуск", commands)
    labels = [item.label for item in matches]
    assert "Запустить" in labels
    assert "Запустить выбранные" in labels
    assert "Пакетный запуск (Vanessa Automation)…" in labels
    assert "Сохранить" not in labels


def test_filter_commands_boosts_recent() -> None:
    commands = [_cmd("Запустить"), _cmd("Запустить выбранные")]
    matches = filter_commands("", commands, recent_ids=["запустить выбранные"])
    assert matches[0].label == "Запустить выбранные"
