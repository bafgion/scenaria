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


def configure_playwright_browsers() -> None:
    bundled = app_root() / "browsers"
    if bundled.is_dir():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(bundled)
        return
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"
    if local.is_dir():
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(local))
