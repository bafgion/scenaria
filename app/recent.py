"""Recent projects and feature files."""

from __future__ import annotations

from pathlib import Path

from app.settings import load_settings, save_settings

_MAX_FEATURES = 8
_MAX_PROJECTS = 5


def _clean_paths(paths: list[str], *, limit: int) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in paths:
        text = str(raw or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if len(result) >= limit:
            break
    return result


def recent_features() -> list[Path]:
    settings = load_settings()
    paths = settings.get("recent_features", [])
    if not isinstance(paths, list):
        return []
    result: list[Path] = []
    for item in paths:
        path = Path(str(item))
        if path.is_file():
            result.append(path)
    return result


def recent_projects() -> list[Path]:
    settings = load_settings()
    paths = settings.get("recent_projects", [])
    if not isinstance(paths, list):
        return []
    result: list[Path] = []
    for item in paths:
        path = Path(str(item))
        if path.is_dir():
            result.append(path)
    return result


def remember_feature(path: Path) -> None:
    settings = load_settings()
    current = [str(path.resolve())]
    if isinstance(settings.get("recent_features"), list):
        current.extend(str(p) for p in settings["recent_features"])
    settings["recent_features"] = _clean_paths(current, limit=_MAX_FEATURES)
    save_settings(settings)


def remember_project(path: Path) -> None:
    settings = load_settings()
    current = [str(path.resolve())]
    if isinstance(settings.get("recent_projects"), list):
        current.extend(str(p) for p in settings["recent_projects"])
    settings["recent_projects"] = _clean_paths(current, limit=_MAX_PROJECTS)
    save_settings(settings)
