"""Named TestClient profiles (Playwright storage_state) for scenarios."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.paths import global_test_clients_dir, project_test_clients_dir

TEST_CLIENT_VERSION = 1


class ClientProfileNotFoundError(RuntimeError):
    def __init__(self, name: str) -> None:
        self.name = name.strip()
        super().__init__(
            f'TestClient «{self.name}» не найден. '
            f"Сохраните клиента: Запуск → TestClient…"
        )


# Backward-compatible alias
TestClientNotFoundError = ClientProfileNotFoundError


@dataclass(frozen=True)
class SavedTestClient:
    name: str
    path: Path
    saved_at: str
    label: str


def _validate_client_name(name: str) -> str:
    text = str(name or "").strip()
    if not text:
        raise ValueError("имя TestClient не может быть пустым")
    for ch in '\\/:*?"<>|':
        if ch in text:
            raise ValueError(f"недопустимый символ в имени TestClient: {ch}")
    return text


def _client_path(name: str, project_root: Path | None = None) -> Path:
    safe_name = _validate_client_name(name)
    if project_root is not None:
        directory = project_test_clients_dir(project_root)
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{safe_name}.json"
    directory = global_test_clients_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{safe_name}.json"


def _client_dirs(project_root: Path | None = None) -> list[Path]:
    dirs: list[Path] = []
    if project_root is not None:
        dirs.append(project_test_clients_dir(project_root))
    dirs.append(global_test_clients_dir())
    return dirs


def _iter_client_files(project_root: Path | None = None) -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []
    for directory in _client_dirs(project_root):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(path)
    return files


def _read_client_file(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _find_client_path(name: str, project_root: Path | None = None) -> Path | None:
    safe_name = _validate_client_name(name)
    for directory in _client_dirs(project_root):
        path = directory / f"{safe_name}.json"
        if path.is_file():
            return path
    return None


def list_test_clients(project_root: Path | None = None) -> list[SavedTestClient]:
    clients: list[SavedTestClient] = []
    for path in _iter_client_files(project_root):
        data = _read_client_file(path)
        if not data:
            continue
        client_name = str(data.get("name", "") or path.stem).strip()
        if not client_name:
            continue
        clients.append(
            SavedTestClient(
                name=client_name,
                path=path,
                saved_at=str(data.get("saved_at", "") or ""),
                label=str(data.get("label", "") or ""),
            )
        )
    clients.sort(key=lambda item: item.name.lower())
    return clients


def save_test_client_from_context(
    context: Any,
    name: str,
    *,
    label: str = "",
    project_root: Path | None = None,
) -> Path:
    client_name = _validate_client_name(name)
    path = _client_path(client_name, project_root)
    state = context.storage_state()
    payload = {
        "version": TEST_CLIENT_VERSION,
        "name": client_name,
        "saved_at": datetime.now(UTC).isoformat(),
        "label": label.strip(),
        "state": state,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def storage_state_for_test_client(name: str, project_root: Path | None = None) -> dict[str, Any] | None:
    path = _find_client_path(name, project_root)
    if path is None:
        return None
    data = _read_client_file(path)
    if not data:
        return None
    state = data.get("state")
    return state if isinstance(state, dict) else None


def test_client_exists(name: str, project_root: Path | None = None) -> bool:
    return storage_state_for_test_client(name, project_root) is not None


def require_test_client(name: str, project_root: Path | None = None) -> dict[str, Any]:
    state = storage_state_for_test_client(name, project_root)
    if state is None:
        raise TestClientNotFoundError(name)
    return state


def remove_test_client(name: str, project_root: Path | None = None) -> bool:
    path = _find_client_path(name, project_root)
    if path is None:
        return False
    try:
        path.unlink(missing_ok=True)  # type: ignore[call-arg]
    except TypeError:
        if path.exists():
            path.unlink()
    return True


def export_test_client(name: str, target: Path, project_root: Path | None = None) -> Path:
    path = _find_client_path(name, project_root)
    if path is None:
        raise FileNotFoundError(name)
    target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def import_test_client(source: Path, project_root: Path | None = None) -> Path:
    data = _read_client_file(source)
    if not data:
        raise ValueError("invalid TestClient file")
    client_name = str(data.get("name", "") or source.stem).strip()
    if not client_name:
        raise ValueError("TestClient file missing name")
    path = _client_path(client_name, project_root)
    path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return path
