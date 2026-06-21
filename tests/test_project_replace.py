"""Tests for project-wide replace."""

from __future__ import annotations

from pathlib import Path

from app.project_replace import apply_files_replace, preview_files_replace


def test_preview_and_apply_replace_in_project(tmp_path: Path) -> None:
    first = tmp_path / "a.feature"
    second = tmp_path / "b.feature"
    first.write_text(
        'Функционал: UI\nСценарий: A\n\tДопустим открыт "https://old.example.com"\n',
        encoding="utf-8",
    )
    second.write_text(
        'Функционал: UI\nСценарий: B\n\tДопустим открыт "https://old.example.com/page"\n',
        encoding="utf-8",
    )
    previews = preview_files_replace(
        [first, second],
        "old.example.com",
        "new.example.com",
    )
    assert len(previews) == 2
    assert sum(item.match_count for item in previews) == 2

    changed = apply_files_replace(
        [first, second],
        "old.example.com",
        "new.example.com",
    )
    assert len(changed) == 2
    assert "new.example.com" in first.read_text(encoding="utf-8")
    assert "new.example.com" in second.read_text(encoding="utf-8")


def test_preview_skips_dirty_paths(tmp_path: Path) -> None:
    feature = tmp_path / "demo.feature"
    feature.write_text(
        'Функционал: UI\nСценарий: Demo\n\tДопустим открыт "https://old.example.com"\n',
        encoding="utf-8",
    )
    previews = preview_files_replace(
        [feature],
        "old.example.com",
        "new.example.com",
        skip_paths={feature},
    )
    assert len(previews) == 1
    assert previews[0].skipped is True


def test_steps_only_skips_scenario_header(tmp_path: Path) -> None:
    feature = tmp_path / "demo.feature"
    feature.write_text(
        'Функционал: old title\nСценарий: old title\n\tДопустим открыт "https://x.com"\n',
        encoding="utf-8",
    )
    previews = preview_files_replace(
        [feature],
        "old title",
        "new title",
        steps_only=True,
    )
    assert previews == []
