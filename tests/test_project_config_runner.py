"""default_runner project config helpers."""

from __future__ import annotations

from pathlib import Path

from app.project_config import default_runner, load_project_config, set_default_runner


def test_set_default_runner_persists(tmp_path: Path) -> None:
    set_default_runner(tmp_path, "vanessa")
    assert default_runner(tmp_path) == "vanessa"
    config = load_project_config(tmp_path)
    assert config["default_runner"] == "vanessa"
