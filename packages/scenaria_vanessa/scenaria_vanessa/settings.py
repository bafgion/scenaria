"""Vanessa add-on settings (stored in settings.json → plugins.vanessa)."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from app.paths import settings_path
from app.project_config import load_project_config

DEFAULTS: dict[str, Any] = {
    "platform_executable": "",
    "platform_mode": "TestManager",
    "platform_extra_args": [],
    "epf_path": "",
    "epf_download_url": "",
    "ib_connection_string": "",
    "user": "",
    "password": "",
    "runs_dir": "",
    "process_timeout_sec": 3600,
    "start_feature_player": True,
    "quiet_install_vanessa_ext": True,
    "install_ext_on_fail": False,
    "log_encoding": "auto",
    "default_report_profile": "junit",
    "report_junit": True,
    "report_allure": False,
    "allure_cli_path": "allure",
    "project_base_params": ".scenaria/va-params.base.json",
    "install_url": "",
    "dry_run_only": False,
}


def _read_settings_file() -> dict[str, Any]:
    path = settings_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def load_vanessa_settings() -> dict[str, Any]:
    data = _read_settings_file()
    plugins = data.get("plugins")
    raw = plugins.get("vanessa", {}) if isinstance(plugins, dict) else {}
    merged = deepcopy(DEFAULTS)
    if isinstance(raw, dict):
        merged.update(raw)
    return merged


def save_vanessa_settings(vanessa: dict[str, Any]) -> None:
    data = _read_settings_file()
    plugins = data.get("plugins")
    if not isinstance(plugins, dict):
        plugins = {}
    payload = deepcopy(DEFAULTS)
    payload.update({key: vanessa[key] for key in vanessa if key in DEFAULTS or key in vanessa})
    plugins["vanessa"] = payload
    data["plugins"] = plugins
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_runs_dir(settings: dict[str, Any] | None = None) -> Path:
    cfg = settings or load_vanessa_settings()
    custom = str(cfg.get("runs_dir", "") or "").strip()
    if custom:
        return Path(custom).expanduser()
    from app.paths import data_dir

    return data_dir() / "vanessa-runs"


def resolve_base_params_path(project_root: Path | None, settings: dict[str, Any] | None = None) -> Path | None:
    if project_root is None:
        return None
    cfg = settings or load_vanessa_settings()
    project_cfg = load_project_config(project_root)
    rel = str(project_cfg.get("va_params_base") or cfg.get("project_base_params") or "").strip()
    if not rel:
        return None
    return (project_root / rel).resolve()


def validate_paths(settings: dict[str, Any] | None = None) -> list[str]:
    cfg = settings or load_vanessa_settings()
    issues: list[str] = []
    platform = Path(str(cfg.get("platform_executable", "") or "")).expanduser()
    if not platform.is_file():
        issues.append("Не указан или не найден исполняемый файл платформы 1С")
    epf = Path(str(cfg.get("epf_path", "") or "")).expanduser()
    if not epf.is_file():
        issues.append("Не указана или не найдена обработка Vanessa (.epf)")
    return issues
