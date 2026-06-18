"""Tests for catalog run selection and batch stop hook."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.mvc.models.catalog_model import CatalogModel, collect_feature_paths_under
from app.run_suite import run_feature_paths


def test_toggle_run_selection_does_not_require_tree_rebuild(tmp_path: Path) -> None:
    feature = tmp_path / "a.feature"
    feature.write_text(
        'Функционал: UI\nСценарий: A\n\tДопустим открыт "https://a.com"\n',
        encoding="utf-8",
    )
    model = CatalogModel()
    model.set_features_root(tmp_path)
    model.toggle_run_selection(feature)
    assert model.run_selection_count == 1
    model.toggle_run_selection(feature)
    assert model.run_selection_count == 0


def test_select_directory_emits_signal(tmp_path: Path) -> None:
    model = CatalogModel()
    received: list[Path] = []
    model.directory_selected.connect(received.append)
    model.set_features_root(tmp_path)
    sub = tmp_path / "smoke"
    sub.mkdir()
    model.select_directory(sub)
    assert received == [sub.resolve()]


def test_set_features_root_same_path_refreshes_tree(tmp_path: Path) -> None:
    model = CatalogModel()
    events: list[object] = []
    model.tree_changed.connect(events.append)
    model.set_features_root(tmp_path)
    assert len(events) == 1
    model.set_features_root(tmp_path)
    assert len(events) == 2


def test_toggle_run_selection(tmp_path: Path) -> None:
    feature = tmp_path / "a.feature"
    feature.write_text(
        'Функционал: UI\nСценарий: A\n\tДопустим открыт "https://a.com"\n',
        encoding="utf-8",
    )
    model = CatalogModel()
    model.toggle_run_selection(feature)
    assert model.run_selection_count == 1
    assert model.is_in_run_selection(feature)
    model.toggle_run_selection(feature)
    assert model.run_selection_count == 0


def test_add_folder_to_run_selection(tmp_path: Path) -> None:
    sub = tmp_path / "smoke"
    sub.mkdir()
    (sub / "one.feature").write_text(
        'Функционал: UI\nСценарий: One\n\tДопустим открыт "https://a.com"\n',
        encoding="utf-8",
    )
    (sub / "two.feature").write_text(
        'Функционал: UI\nСценарий: Two\n\tДопустим открыт "https://b.com"\n',
        encoding="utf-8",
    )
    model = CatalogModel()
    model.add_folder_to_run_selection(sub)
    assert model.run_selection_count == 2
    paths = collect_feature_paths_under(sub)
    assert len(paths) == 2


def test_run_feature_paths_honors_should_stop(tmp_path: Path) -> None:
    for name in ("a.feature", "b.feature"):
        (tmp_path / name).write_text(
            f'Функционал: UI\nСценарий: {name}\n\tДопустим открыт "https://example.com"\n',
            encoding="utf-8",
        )

    calls = {"count": 0}

    def should_stop() -> bool:
        return calls["count"] >= 1

    with patch("app.run_suite.run_feature_file") as run_file:
        run_file.return_value = {"success": True, "path": tmp_path / "a.feature"}
        cases = run_feature_paths(
            [tmp_path],
            should_stop=should_stop,
            on_case_start=lambda _path: calls.__setitem__("count", calls["count"] + 1),
        )

    assert len(cases) == 1
    assert run_file.call_count == 1
