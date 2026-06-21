"""Tests for catalog tag filtering."""

from __future__ import annotations

from pathlib import Path

from app.mvc.models.catalog_model import (
    build_catalog_view_state,
    collect_feature_paths_with_tag,
    collect_project_tags,
    count_feature_files,
    parse_catalog_filter,
)


def test_parse_catalog_filter_at_tag() -> None:
    assert parse_catalog_filter("@smoke") == ("", "smoke")
    assert parse_catalog_filter("tag:regression") == ("", "regression")
    assert parse_catalog_filter("login") == ("login", "")


def test_filter_tree_by_tag(tmp_path: Path) -> None:
    (tmp_path / "a.feature").write_text(
        "Функционал: UI\n@smoke\nСценарий: A\n\tДопустим открыт \"https://a.com\"\n",
        encoding="utf-8",
    )
    (tmp_path / "b.feature").write_text(
        "Функционал: UI\n@wip\nСценарий: B\n\tДопустим открыт \"https://b.com\"\n",
        encoding="utf-8",
    )
    state = build_catalog_view_state(tmp_path, "@smoke")
    assert count_feature_files(state.tree) == 1
    assert state.tree is not None
    assert state.tree.children[0].name == "a"


def test_collect_feature_paths_with_tag(tmp_path: Path) -> None:
    (tmp_path / "a.feature").write_text(
        "Функционал: UI\n@smoke\nСценарий: A\n\tДопустим открыт \"https://a.com\"\n",
        encoding="utf-8",
    )
    (tmp_path / "b.feature").write_text(
        "Функционал: UI\nСценарий: B\n\tДопустим открыт \"https://b.com\"\n",
        encoding="utf-8",
    )
    paths = collect_feature_paths_with_tag(tmp_path, "smoke")
    assert len(paths) == 1
    assert paths[0].stem == "a"


def test_collect_project_tags(tmp_path: Path) -> None:
    (tmp_path / "a.feature").write_text(
        "Функционал: UI\n@smoke\n@catalog\nСценарий: A\n\tДопустим открыт \"https://a.com\"\n",
        encoding="utf-8",
    )
    tags = collect_project_tags(tmp_path)
    assert tags == ["catalog", "smoke"]
