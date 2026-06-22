"""Detect and install Playwright browser engines (chromium, firefox, webkit)."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

from app.browser_config import BROWSER_ENGINE_LABELS, normalize_browser_engine
from app.paths import (
    browser_cache_candidates,
    configure_playwright_browsers,
    install_playwright_browsers_path,
)

StatusCallback = Callable[[str], None]


def find_browser_executable(cache: Path, engine: str) -> Path | None:
    """Locate a browser binary under a Playwright cache directory."""
    prefix = {
        "chromium": "chromium-",
        "firefox": "firefox-",
        "webkit": "webkit-",
    }.get(engine)
    if prefix is None or not cache.is_dir():
        return None

    folders = sorted(
        (item for item in cache.iterdir() if item.is_dir() and item.name.startswith(prefix)),
        key=lambda item: item.name,
        reverse=True,
    )
    for folder in folders:
        if engine == "chromium":
            candidates = (
                folder / "chrome-win64" / "chrome.exe",
                folder / "chrome-linux" / "chrome",
                folder / "chrome-mac" / "Chromium.app" / "Contents" / "MacOS" / "Chromium",
            )
        elif engine == "firefox":
            candidates = (
                folder / "firefox" / "firefox.exe",
                folder / "firefox" / "firefox",
            )
        else:
            candidates = (folder / "Playwright.exe", folder / "pw_run.sh")

        for executable in candidates:
            if executable.is_file():
                return executable
    return None


def _playwright_install_command(engine: str, *, cache: Path) -> tuple[list[str], dict[str, str]]:
    """Build argv/env for ``playwright install`` (works in dev and frozen exe)."""
    from playwright._impl._driver import compute_driver_executable, get_driver_env

    env = get_driver_env()
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(cache)
    driver_executable, driver_cli = compute_driver_executable()
    return [driver_executable, driver_cli, "install", engine], env


def browser_install_status(engine: str) -> tuple[bool, str]:
    """Return whether the engine binary exists and its path or a short reason."""
    resolved = normalize_browser_engine(engine)
    label = BROWSER_ENGINE_LABELS.get(resolved, resolved)
    configure_playwright_browsers(engine=resolved)

    for cache in browser_cache_candidates(engine=resolved):
        executable = find_browser_executable(cache, resolved)
        if executable is not None:
            return True, str(executable)

    searched = ", ".join(str(path) for path in browser_cache_candidates(engine=resolved))
    return False, f"{label} не установлен (каталоги: {searched})"


def install_browser_engine(
    engine: str,
    *,
    on_line: StatusCallback | None = None,
) -> Path:
    resolved = normalize_browser_engine(engine)
    label = BROWSER_ENGINE_LABELS.get(resolved, resolved)
    cache = install_playwright_browsers_path(engine=resolved)
    configure_playwright_browsers(engine=resolved)
    if on_line is not None:
        on_line(f"Установка {label} в {cache}…")

    command, env = _playwright_install_command(resolved, cache=cache)
    output_lines: list[str] = []
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    if process.stdout is not None:
        for line in process.stdout:
            text = line.strip()
            if not text:
                continue
            output_lines.append(text)
            if on_line is not None:
                on_line(text)
    return_code = process.wait()
    if return_code != 0:
        tail = "\n".join(output_lines[-8:])
        detail = tail or f"код {return_code}"
        raise RuntimeError(f"Не удалось установить {label}:\n{detail}")

    installed, detail = browser_install_status(resolved)
    if not installed:
        raise RuntimeError(
            f"После установки {label} недоступен: {detail}\n"
            f"Каталог браузеров: {cache}"
        )
    return Path(detail)


def ensure_browser_engine(
    engine: str,
    *,
    on_line: StatusCallback | None = None,
) -> Path:
    installed, detail = browser_install_status(engine)
    if installed:
        configure_playwright_browsers(engine=engine)
        return Path(detail)
    return install_browser_engine(engine, on_line=on_line)
