"""Tests for .scenaria/project.json helpers."""

from __future__ import annotations

import json
from pathlib import Path

from app.project_config import default_runner, load_project_config, save_project_config


def test_default_runner_without_project() -> None:
    assert default_runner(None) == "playwright"


def test_migrates_vanessa_runner_alias(tmp_path: Path) -> None:
    config_dir = tmp_path / ".scenaria"
    config_dir.mkdir()
    (config_dir / "project.json").write_text(
        json.dumps({"vanessa_runner": "vanessa"}),
        encoding="utf-8",
    )
    config = load_project_config(tmp_path)
    assert config["default_runner"] == "vanessa"
    assert default_runner(tmp_path) == "vanessa"


def test_save_and_load_project_config(tmp_path: Path) -> None:
    data = {"default_runner": "playwright", "features_root": "tests/features"}
    path = save_project_config(tmp_path, data)
    assert path.is_file()
    loaded = load_project_config(tmp_path)
    assert loaded["features_root"] == "tests/features"
