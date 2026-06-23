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


def project_test_clients_dir(project_root: Path) -> Path:
    return project_root / ".scenaria" / "test_clients"


def global_test_clients_dir() -> Path:
    path = data_dir() / "test_clients"
    path.mkdir(parents=True, exist_ok=True)
    return path


def project_snippets_path(project_root: Path) -> Path:
    return project_root / ".scenaria" / "snippets.json"


def global_snippets_path() -> Path:
    return data_dir() / "snippets.json"


def plugins_dir() -> Path:
    path = data_dir() / "plugins"
    path.mkdir(parents=True, exist_ok=True)
    return path


def examples_dir() -> Path:
    """Shipped beginner sample scenarios (portable: next to exe; dev: repo root)."""
    for candidate in (
        app_root() / "examples",
        bundled_root() / "examples",
        Path(__file__).resolve().parent.parent / "examples",
    ):
        if candidate.is_dir():
            return candidate
    return Path(__file__).resolve().parent.parent / "examples"


def ms_playwright_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"


def bundled_browsers_dir() -> Path:
    return app_root() / "browsers"


_ENGINE_PREFIXES: dict[str, str] = {
    "chromium": "chromium-",
    "firefox": "firefox-",
    "webkit": "webkit-",
}


def directory_has_engine(path: Path, engine: str) -> bool:
    prefix = _ENGINE_PREFIXES.get(engine, "")
    if not prefix or not path.is_dir():
        return False
    try:
        return any(
            item.is_dir() and item.name.startswith(prefix) for item in path.iterdir()
        )
    except OSError:
        return False


def browser_cache_candidates(*, engine: str | None = None) -> list[Path]:
    """Ordered Playwright cache directories to search for browser binaries."""
    bundled = bundled_browsers_dir()
    local = ms_playwright_dir()
    resolved = None
    if engine:
        from app.browser_config import normalize_browser_engine

        resolved = normalize_browser_engine(engine)

    candidates: list[Path] = []
    if bundled.is_dir() and directory_has_engine(bundled, "chromium"):
        candidates.append(bundled)
    if local.is_dir():
        candidates.append(local)
    elif local not in candidates:
        candidates.append(local)

    if resolved:
        preferred = [path for path in candidates if directory_has_engine(path, resolved)]
        if preferred:
            return preferred
    return candidates


def resolve_playwright_browsers_path(*, engine: str | None = None) -> Path:
    if engine is None:
        from app.browser_config import load_browser_engine

        engine = load_browser_engine()
    candidates = browser_cache_candidates(engine=engine)
    return candidates[0] if candidates else ms_playwright_dir()


def install_playwright_browsers_path(*, engine: str) -> Path:
    """Writable cache directory for ``playwright install``."""
    bundled = bundled_browsers_dir()
    local = ms_playwright_dir()
    if bundled.is_dir() and directory_has_engine(bundled, "chromium"):
        bundled.mkdir(parents=True, exist_ok=True)
        return bundled
    local.mkdir(parents=True, exist_ok=True)
    return local


def configure_playwright_browsers(*, engine: str | None = None) -> None:
    path = resolve_playwright_browsers_path(engine=engine)
    path.mkdir(parents=True, exist_ok=True)
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(path)
