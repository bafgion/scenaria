"""Project root persistence and recovery."""

from __future__ import annotations

from pathlib import Path

from app.feature_store import (
    clear_root,
    get_root,
    is_ephemeral_project_path,
    resolve_project_root,
    set_root,
)
from app.recent import remember_feature, remember_project
from app.settings import load_settings, save_settings


def test_is_ephemeral_project_path_detects_pytest_tmp(tmp_path: Path) -> None:
    pytest_dir = tmp_path / "pytest-of-user" / "test_set_features_root_same_pa0"
    pytest_dir.mkdir(parents=True)
    assert is_ephemeral_project_path(pytest_dir)


def test_get_root_clears_ephemeral_path(tmp_path: Path) -> None:
    pytest_dir = tmp_path / "pytest-of-user" / "test_set_features_root_same_pa0"
    pytest_dir.mkdir(parents=True)
    set_root(pytest_dir)
    assert get_root() is None
    assert load_settings()["features_root"] == ""


def test_resolve_project_root_from_recent_features(tmp_path: Path) -> None:
    project = tmp_path / "my-project"
    project.mkdir()
    feature = project / "login.feature"
    feature.write_text(
        'Функционал: UI\nСценарий: Login\n\tДопустим открыт "https://example.com"\n',
        encoding="utf-8",
    )
    clear_root()
    remember_feature(feature)
    resolved = resolve_project_root()
    assert resolved == project.resolve()
    assert get_root() == project.resolve()


def test_resolve_project_root_from_open_tabs(tmp_path: Path) -> None:
    project = tmp_path / "tabs-project"
    project.mkdir()
    feature = project / "checkout.feature"
    feature.write_text(
        'Функционал: UI\nСценарий: Checkout\n\tДопустим открыт "https://example.com"\n',
        encoding="utf-8",
    )
    clear_root()
    save_settings(
        {
            **load_settings(),
            "open_tabs": [{"path": str(feature), "title": feature.name, "text": "", "key": str(feature)}],
        }
    )
    resolved = resolve_project_root()
    assert resolved == project.resolve()


def test_resolve_project_root_prefers_recent_projects(tmp_path: Path) -> None:
    project = tmp_path / "recent-project"
    project.mkdir()
    clear_root()
    remember_project(project)
    resolved = resolve_project_root()
    assert resolved == project.resolve()
