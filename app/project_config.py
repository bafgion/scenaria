"""Per-project Scenaria configuration (``.scenaria/project.json``)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_PROJECT_CONFIG: dict[str, Any] = {
    "default_runner": "playwright",
    "features_root": "features",
    "va_params_base": ".scenaria/va-params.base.json",
}


def project_config_path(project_root: Path) -> Path:
    return project_root / ".scenaria" / "project.json"


def load_project_config(project_root: Path | None) -> dict[str, Any]:
    if project_root is None:
        return dict(DEFAULT_PROJECT_CONFIG)
    path = project_config_path(project_root)
    if not path.is_file():
        return dict(DEFAULT_PROJECT_CONFIG)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_PROJECT_CONFIG)
    if not isinstance(data, dict):
        return dict(DEFAULT_PROJECT_CONFIG)
    merged = dict(DEFAULT_PROJECT_CONFIG)
    merged.update(data)
    if "default_runner" not in data and data.get("vanessa_runner"):
        merged["default_runner"] = str(data["vanessa_runner"])
    return merged


def save_project_config(project_root: Path, data: dict[str, Any]) -> Path:
    path = project_config_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def default_runner(project_root: Path | None) -> str:
    value = str(load_project_config(project_root).get("default_runner", "playwright")).strip()
    if value in {"", "ask"}:
        return "playwright"
    return value
