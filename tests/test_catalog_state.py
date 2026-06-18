"""Tests for catalog empty-state messages."""

from __future__ import annotations

from pathlib import Path

from app.mvc.models.catalog_model import build_catalog_view_state, count_feature_files


def test_no_project_open() -> None:
    state = build_catalog_view_state(None, "")
    assert state.tree is None
    assert state.empty_title == "Проект не открыт"
    assert "Открыть проект" in (state.empty_hint or "")


def test_empty_project_folder(tmp_path: Path) -> None:
    state = build_catalog_view_state(tmp_path, "")
    assert state.empty_title == "Нет сценариев"
    assert count_feature_files(state.tree) == 0


def test_filter_without_matches(tmp_path: Path) -> None:
    (tmp_path / "checkout.feature").write_text(
        'Функционал: UI\nСценарий: Checkout\n\tДопустим открыт "https://a.com"\n',
        encoding="utf-8",
    )
    state = build_catalog_view_state(tmp_path, "zzz")
    assert state.empty_title == "Ничего не найдено"
    assert "zzz" in (state.empty_hint or "")


def test_project_with_files_has_no_empty_message(tmp_path: Path) -> None:
    (tmp_path / "login.feature").write_text(
        'Функционал: UI\nСценарий: Login\n\tДопустим открыт "https://a.com"\n',
        encoding="utf-8",
    )
    state = build_catalog_view_state(tmp_path, "")
    assert state.empty_title is None
    assert count_feature_files(state.tree) == 1


def test_broken_feature_shows_parse_error(tmp_path: Path) -> None:
    (tmp_path / "broken.feature").write_text(
        "Функционал: UI\nСценарий: Bad\n\tИ кликаю по кнопке\n",
        encoding="utf-8",
    )
    state = build_catalog_view_state(tmp_path, "")
    assert state.tree is not None
    file_node = state.tree.children[0]
    assert file_node.parse_error is not None
