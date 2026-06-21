"""Paths and environment for portable exe."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from app.brand import APP_DATA_DIR


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def bundled_root() -> Path:
    """PyInstaller data root (_MEIPASS / _internal) for frozen builds."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        internal = app_root() / "_internal"
        if internal.is_dir():
            return internal
    return app_root()


def data_dir() -> Path:
    if getattr(sys, "frozen", False):
        path = app_root() / "data"
    else:
        path = Path(os.environ.get("APPDATA", ".")) / APP_DATA_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def traces_dir() -> Path:
    path = data_dir() / "traces"
    path.mkdir(parents=True, exist_ok=True)
    return path


def screenshots_dir() -> Path:
    path = data_dir() / "screenshots"
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path() -> Path:
    return data_dir() / "settings.json"


def exports_dir() -> Path:
    path = data_dir() / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def reports_dir() -> Path:
    path = data_dir() / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def global_sessions_dir() -> Path:
    path = data_dir() / "sessions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def project_sessions_dir(project_root: Path) -> Path:
    return project_root / ".scenaria" / "sessions"


def project_snippets_path(project_root: Path) -> Path:
    return project_root / ".scenaria" / "snippets.json"


def global_snippets_path() -> Path:
    return data_dir() / "snippets.json"


def plugins_dir() -> Path:
    path = data_dir() / "plugins"
    path.mkdir(parents=True, exist_ok=True)
    return path


def configure_playwright_browsers() -> None:
    bundled = app_root() / "browsers"
    if bundled.is_dir():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(bundled)
        return
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"
    if local.is_dir():
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(local))
