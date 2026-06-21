"""Discover runner plugins from entry points and APPDATA folders."""

from __future__ import annotations

import importlib
import json
import logging
import sys
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any

from app import paths
from app.plugins.playwright_runner import PlaywrightRunner
from app.version import app_version, version_tuple

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "scenaria.plugins"
KNOWN_OPTIONAL_PLUGINS: dict[str, str] = {
    "vanessa": "Vanessa Automation",
}


def builtin_playwright_runner() -> PlaywrightRunner:
    return PlaywrightRunner()


def _min_scenaria_ok(manifest: dict[str, Any]) -> tuple[bool, str]:
    required = str(manifest.get("min_scenaria", "") or "").strip()
    if not required:
        return True, ""
    if version_tuple(app_version()) >= version_tuple(required):
        return True, ""
    return False, f"Требуется Scenaria {required} или новее (установлено {app_version()})"


def _load_runner_object(raw: Any):
    if raw is None:
        raise ValueError("пустой объект плагина")
    if isinstance(raw, type):
        return raw()
    if callable(raw) and not hasattr(raw, "id"):
        return raw()
    return raw


def _import_entry(entry: str, plugin_root: Path | None = None):
    if ":" not in entry:
        raise ValueError(f"неверный entry: {entry}")
    module_name, attr_name = entry.split(":", 1)
    if plugin_root is not None:
        root = str(plugin_root.resolve())
        if root not in sys.path:
            sys.path.insert(0, root)
    module = importlib.import_module(module_name)
    target = getattr(module, attr_name)
    if isinstance(target, type):
        return target()
    return _load_runner_object(target)


def _read_manifest(plugin_dir: Path) -> dict[str, Any]:
    manifest_path = plugin_dir / "plugin.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"нет plugin.json в {plugin_dir}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("plugin.json должен быть объектом JSON")
    return data


def load_folder_plugin(plugin_dir: Path) -> tuple[Any | None, str | None]:
    try:
        manifest = _read_manifest(plugin_dir)
        ok, reason = _min_scenaria_ok(manifest)
        if not ok:
            return None, reason
        entry = str(manifest.get("entry", "") or "").strip()
        if not entry:
            return None, "plugin.json: отсутствует entry"
        plugin_id = str(manifest.get("id", "") or plugin_dir.name).strip()
        runner = _import_entry(entry, plugin_dir)
        if not getattr(runner, "id", None):
            runner.id = plugin_id  # type: ignore[attr-defined]
        return runner, None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def load_entry_point_plugins() -> list[tuple[str, Any | None, str | None]]:
    results: list[tuple[str, Any | None, str | None]] = []
    try:
        eps = entry_points(group=ENTRY_POINT_GROUP)
    except TypeError:
        eps = entry_points().get(ENTRY_POINT_GROUP, [])
    for ep in eps:
        plugin_id = ep.name
        try:
            runner = _load_runner_object(ep.load())
            results.append((plugin_id, runner, None))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось загрузить entry point %s: %s", plugin_id, exc)
            results.append((plugin_id, None, str(exc)))
    return results


def load_folder_plugins(extra_roots: list[Path] | None = None) -> list[tuple[str, Any | None, str | None]]:
    results: list[tuple[str, Any | None, str | None]] = []
    roots = [paths.plugins_dir(), *(extra_roots or [])]
    seen: set[str] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            plugin_id = child.name
            if plugin_id in seen:
                continue
            seen.add(plugin_id)
            runner, error = load_folder_plugin(child)
            results.append((plugin_id, runner, error))
    return results


def discover_plugins(project_root: Path | None = None) -> tuple[dict[str, Any], dict[str, str]]:
    runners: dict[str, Any] = {PlaywrightRunner.id: builtin_playwright_runner()}
    errors: dict[str, str] = {}

    project_plugins = (
        project_root / ".scenaria" / "plugins" if project_root is not None else None
    )
    extra = [project_plugins] if project_plugins is not None else None

    for plugin_id, runner, error in load_entry_point_plugins():
        if error:
            errors[plugin_id] = error
            continue
        if runner is None:
            continue
        rid = str(getattr(runner, "id", plugin_id))
        if rid == PlaywrightRunner.id:
            continue
        runners[rid] = runner

    for plugin_id, runner, error in load_folder_plugins(extra):
        if error:
            errors[plugin_id] = error
            continue
        if runner is None:
            continue
        rid = str(getattr(runner, "id", plugin_id))
        if rid == PlaywrightRunner.id:
            continue
        runners[rid] = runner

    return runners, errors
