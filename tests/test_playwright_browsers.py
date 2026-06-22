"""Tests for Playwright browser engine installation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.paths import browser_cache_candidates, resolve_playwright_browsers_path
from app.playwright_browsers import (
    browser_install_status,
    ensure_browser_engine,
    find_browser_executable,
    install_browser_engine,
)


def test_find_browser_executable_chromium(tmp_path: Path) -> None:
    root = tmp_path / "chromium-1223" / "chrome-win64"
    root.mkdir(parents=True)
    exe = root / "chrome.exe"
    exe.write_bytes(b"x")
    found = find_browser_executable(tmp_path, "chromium")
    assert found == exe


def test_browser_cache_candidates_ignore_empty_bundled_dir(
    monkeypatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    empty_browsers = repo / "browsers"
    empty_browsers.mkdir()
    local = tmp_path / "ms-playwright"
    local.mkdir()
    (local / "chromium-1").mkdir()

    monkeypatch.setattr("app.paths.app_root", lambda: repo)
    monkeypatch.setattr("app.paths.ms_playwright_dir", lambda: local)

    candidates = browser_cache_candidates(engine="chromium")
    assert candidates == [local]


def test_resolve_playwright_browsers_path_uses_ms_playwright_when_bundled_empty(
    monkeypatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "browsers").mkdir()
    local = tmp_path / "ms-playwright"
    local.mkdir()
    (local / "chromium-1").mkdir()

    monkeypatch.setattr("app.paths.app_root", lambda: repo)
    monkeypatch.setattr("app.paths.ms_playwright_dir", lambda: local)

    assert resolve_playwright_browsers_path(engine="chromium") == local


def test_browser_install_status_detects_missing_engine(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.playwright_browsers.browser_cache_candidates",
        lambda engine=None: [tmp_path],
    )
    installed, detail = browser_install_status("firefox")
    assert installed is False
    assert "Firefox" in detail


def test_browser_install_status_detects_present_file(tmp_path: Path, monkeypatch) -> None:
    folder = tmp_path / "firefox-1522" / "firefox"
    folder.mkdir(parents=True)
    exe = folder / "firefox.exe"
    exe.write_bytes(b"x")
    monkeypatch.setattr(
        "app.playwright_browsers.browser_cache_candidates",
        lambda engine=None: [tmp_path],
    )
    installed, detail = browser_install_status("firefox")
    assert installed is True
    assert detail == str(exe)


def test_install_browser_engine_runs_playwright_cli(monkeypatch, tmp_path: Path) -> None:
    lines: list[str] = []

    def fake_status(engine: str) -> tuple[bool, str]:
        return True, str(tmp_path / "chromium.exe")

    def fake_install_command(engine: str, *, cache: Path) -> tuple[list[str], dict[str, str]]:
        return ["node.exe", "cli.js", "install", engine], {"PLAYWRIGHT_BROWSERS_PATH": str(cache)}

    def fake_popen(command, **kwargs):
        assert command == ["node.exe", "cli.js", "install", "chromium"]
        assert kwargs["env"]["PLAYWRIGHT_BROWSERS_PATH"] == str(tmp_path)
        process = MagicMock()
        process.stdout = iter(["Downloading Chromium\n", "Done\n"])
        process.wait.return_value = 0
        return process

    monkeypatch.setattr("app.playwright_browsers.browser_install_status", fake_status)
    monkeypatch.setattr("app.playwright_browsers.install_playwright_browsers_path", lambda engine: tmp_path)
    monkeypatch.setattr("app.playwright_browsers._playwright_install_command", fake_install_command)
    monkeypatch.setattr("app.playwright_browsers.subprocess.Popen", fake_popen)
    path = install_browser_engine("chromium", on_line=lines.append)
    assert path == tmp_path / "chromium.exe"
    assert any("Downloading" in line for line in lines)


def test_playwright_install_command_uses_driver(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "playwright._impl._driver.compute_driver_executable",
        lambda: ("node.exe", "cli.js"),
    )

    from app.playwright_browsers import _playwright_install_command

    command, env = _playwright_install_command("firefox", cache=tmp_path)
    assert command == ["node.exe", "cli.js", "install", "firefox"]
    assert env["PLAYWRIGHT_BROWSERS_PATH"] == str(tmp_path)


def test_ensure_browser_engine_skips_install_when_present(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "app.playwright_browsers.browser_install_status",
        lambda engine: (True, str(tmp_path / "webkit.exe")),
    )

    called = False

    def fail_install(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("install should not run")

    monkeypatch.setattr("app.playwright_browsers.install_browser_engine", fail_install)
    path = ensure_browser_engine("webkit")
    assert path == tmp_path / "webkit.exe"
    assert called is False


def test_ensure_browser_engine_installs_when_missing(monkeypatch, tmp_path: Path) -> None:
    statuses = [False, True]

    def fake_status(engine: str) -> tuple[bool, str]:
        if statuses[0]:
            statuses[0] = False
            return False, "missing"
        return True, str(tmp_path / "firefox.exe")

    monkeypatch.setattr("app.playwright_browsers.browser_install_status", fake_status)
    monkeypatch.setattr(
        "app.playwright_browsers.install_browser_engine",
        lambda engine, on_line=None: tmp_path / "firefox.exe",
    )
    path = ensure_browser_engine("firefox")
    assert path == tmp_path / "firefox.exe"


def test_launch_browser_with_active_playwright_session(monkeypatch, tmp_path: Path) -> None:
    folder = tmp_path / "chromium-1223" / "chrome-win64"
    folder.mkdir(parents=True)
    exe = folder / "chrome.exe"
    exe.write_bytes(b"x")
    monkeypatch.setattr(
        "app.playwright_browsers.browser_cache_candidates",
        lambda engine=None: [tmp_path],
    )

    playwright = MagicMock()
    chromium = MagicMock()
    playwright.chromium = chromium

    from app.browser_config import launch_browser

    launch_browser(playwright, engine="chromium", headless=True)
    chromium.launch.assert_called_once()
