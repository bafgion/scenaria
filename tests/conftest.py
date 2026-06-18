"""Pytest configuration."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Never write tests into the user's real %APPDATA% settings."""
    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr("app.paths.settings_path", lambda: settings_file)
    monkeypatch.setattr("app.settings.settings_path", lambda: settings_file)
    return settings_file
