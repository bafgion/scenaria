"""Tests for Vanessa settings persistence."""

from __future__ import annotations

from pathlib import Path

from scenaria_vanessa.settings import load_vanessa_settings, save_vanessa_settings, validate_paths


def test_save_and_load_vanessa_settings(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("scenaria_vanessa.settings.settings_path", lambda: tmp_path / "settings.json")
    save_vanessa_settings({"platform_executable": "C:/1c/1cv8c.exe", "epf_path": "C:/va.epf"})
    loaded = load_vanessa_settings()
    assert loaded["platform_executable"] == "C:/1c/1cv8c.exe"
    assert loaded["epf_path"] == "C:/va.epf"


def test_validate_paths_reports_missing_files() -> None:
    issues = validate_paths({"platform_executable": "", "epf_path": ""})
    assert len(issues) == 2
