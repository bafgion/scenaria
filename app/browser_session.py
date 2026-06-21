"""Browser cookie/localStorage sessions scoped by origin."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.http_auth import origin_for_url
from app.paths import global_sessions_dir, project_sessions_dir

SESSION_VERSION = 1


@dataclass(frozen=True)
class SavedSession:
    origin: str
    path: Path
    saved_at: str
    label: str


def session_origin(url: str) -> str:
    text = (url or "").strip()
    lowered = text.lower()
    if not text or lowered.startswith(("about:", "data:", "file:", "chrome:")):
        return ""
    try:
        return origin_for_url(text)
    except ValueError:
        return ""


def _origin_key(origin: str) -> str:
    return hashlib.sha256(origin.encode("utf-8")).hexdigest()[:16]


def _writable_session_path(origin: str, project_root: Path | None = None) -> Path:
    key = _origin_key(origin)
    if project_root is not None:
        directory = project_sessions_dir(project_root)
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{key}.json"
    directory = global_sessions_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{key}.json"


def _iter_session_files(project_root: Path | None = None) -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []
    for directory in _session_dirs(project_root):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(path)
    return files


def _session_dirs(project_root: Path | None = None) -> list[Path]:
    dirs: list[Path] = []
    if project_root is not None:
        dirs.append(project_sessions_dir(project_root))
    dirs.append(global_sessions_dir())
    return dirs


def _read_session_file(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _find_session_path(origin: str, project_root: Path | None = None) -> Path | None:
    key = _origin_key(origin)
    for directory in _session_dirs(project_root):
        path = directory / f"{key}.json"
        if path.is_file():
            return path
    return None


def list_saved_sessions(project_root: Path | None = None) -> list[SavedSession]:
    sessions: list[SavedSession] = []
    for path in _iter_session_files(project_root):
        data = _read_session_file(path)
        if not data:
            continue
        origin = str(data.get("origin", "") or "").strip()
        if not origin:
            continue
        sessions.append(
            SavedSession(
                origin=origin,
                path=path,
                saved_at=str(data.get("saved_at", "") or ""),
                label=str(data.get("label", "") or ""),
            )
        )
    sessions.sort(key=lambda item: item.origin)
    return sessions


def save_session_from_context(
    context: Any,
    origin: str,
    *,
    label: str = "",
    project_root: Path | None = None,
) -> Path:
    origin = origin.strip()
    if not origin:
        raise ValueError("origin is required")
    path = _writable_session_path(origin, project_root)
    state = context.storage_state()
    payload = {
        "version": SESSION_VERSION,
        "origin": origin,
        "saved_at": datetime.now(UTC).isoformat(),
        "label": label.strip(),
        "state": state,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def storage_state_for_url(url: str, project_root: Path | None = None) -> dict[str, Any] | None:
    origin = session_origin(url)
    if not origin:
        return None
    path = _find_session_path(origin, project_root)
    if path is None:
        return None
    data = _read_session_file(path)
    if not data:
        return None
    state = data.get("state")
    return state if isinstance(state, dict) else None


def remove_saved_session(origin: str, project_root: Path | None = None) -> bool:
    path = _find_session_path(origin, project_root)
    if path is None:
        return False
    try:
        path.unlink(missing_ok=True)  # type: ignore[call-arg]
    except TypeError:
        if path.exists():
            path.unlink()
    return True


def export_session(origin: str, target: Path, project_root: Path | None = None) -> Path:
    path = _find_session_path(origin, project_root)
    if path is None:
        raise FileNotFoundError(origin)
    target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def import_session(source: Path, project_root: Path | None = None) -> Path:
    data = _read_session_file(source)
    if not data:
        raise ValueError("invalid session file")
    origin = str(data.get("origin", "") or "").strip()
    if not origin:
        raise ValueError("session file missing origin")
    path = _writable_session_path(origin, project_root)
    path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return path
