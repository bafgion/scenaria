"""Persistent user preferences."""

from __future__ import annotations

import json
from typing import Any

from app.paths import settings_path
from app.selector_build import DEFAULT_SELECTOR_PRIORITY, normalize_selector_priority

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
    "use_saved_browser_session": True,
    "selector_priority": list(DEFAULT_SELECTOR_PRIORITY),
    "hover_record_enabled": False,
    "hover_record_min_ms": 300,
    "scroll_before_click": False,
    "save_html_reports": True,
    "open_html_report_after_run": False,
    "plugins": {},
    "parallel_workers": 1,
    "max_loop_iterations": 100,
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
    if isinstance(data, dict):
        for key, value in data.items():
            if key not in DEFAULTS:
                merged[key] = value
    merged["selector_priority"] = normalize_selector_priority(merged.get("selector_priority"))
    return merged


def save_settings(settings: dict[str, Any]) -> None:
    path = settings_path()
    payload = dict(DEFAULTS)
    for key in DEFAULTS:
        if key in settings:
            payload[key] = settings[key]
    if isinstance(settings, dict):
        for key, value in settings.items():
            if key not in DEFAULTS:
                payload[key] = value
    payload["selector_priority"] = normalize_selector_priority(payload.get("selector_priority"))
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
