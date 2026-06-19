"""Persistent user preferences."""

from __future__ import annotations

import json
from typing import Any

from app.paths import settings_path

DEFAULTS: dict[str, Any] = {
    "filter_recording": False,
    "nav_only_recording": False,
    "headless": False,
    "autosave_enabled": True,
    "features_root": "",
    "recent_features": [],
    "recent_projects": [],
    "steps_panel_height": 160,
    "steps_panel_visible": True,
    "open_tabs": [],
    "active_tab_index": 0,
    "check_updates_on_startup": True,
    "dismissed_update_version": "",
    "http_auth": {},
}


def load_settings() -> dict[str, Any]:
    path = settings_path()
    if not path.exists():
        return dict(DEFAULTS)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)
    merged = dict(DEFAULTS)
    for key in DEFAULTS:
        if key in data:
            merged[key] = data[key]
    return merged


def save_settings(settings: dict[str, Any]) -> None:
    path = settings_path()
    payload = dict(DEFAULTS)
    for key in DEFAULTS:
        if key in settings:
            payload[key] = settings[key]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
