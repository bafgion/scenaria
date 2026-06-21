"""Install and uninstall zip add-ons into APPDATA."""

from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from app import paths
from app.plugins.loader import _min_scenaria_ok
from app.plugins.registry import get_registry, reset_registry
from app.update.checker import UpdateCheckError, _api_url, _direct_release_url, _request_json
from app.update.http_download import download_url_resilient
from app.version import app_version


class PluginInstallError(Exception):
    pass


def list_installed_plugins() -> list[dict[str, Any]]:
    root = paths.plugins_dir()
    if not root.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        manifest_path = child / "plugin.json"
        if not manifest_path.is_file():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            manifest = {}
        if not isinstance(manifest, dict):
            manifest = {}
        items.append(
            {
                "id": str(manifest.get("id", child.name)),
                "name": str(manifest.get("name", child.name)),
                "version": str(manifest.get("version", "")),
                "path": str(child),
            }
        )
    return items


def _validate_zip_contents(extract_root: Path) -> dict[str, Any]:
    manifest_files = list(extract_root.rglob("plugin.json"))
    if not manifest_files:
        raise PluginInstallError("В архиве нет plugin.json")
    manifest_path = manifest_files[0]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise PluginInstallError("plugin.json должен быть объектом JSON")
    ok, reason = _min_scenaria_ok(manifest)
    if not ok:
        raise PluginInstallError(reason)
    plugin_id = str(manifest.get("id", "") or "").strip()
    if not plugin_id:
        raise PluginInstallError("plugin.json: отсутствует id")
    entry = str(manifest.get("entry", "") or "").strip()
    if not entry:
        raise PluginInstallError("plugin.json: отсутствует entry")
    return manifest


def _install_extracted(extract_root: Path, manifest: dict[str, Any]) -> Path:
    plugin_id = str(manifest["id"])
    target = paths.plugins_dir() / plugin_id
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    manifest_path = next(extract_root.rglob("plugin.json"))
    payload_root = manifest_path.parent
    for item in payload_root.iterdir():
        dest = target / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)
    return target


def install_from_zip(zip_path: Path, *, plugin_id: str | None = None) -> Path:
    zip_path = zip_path.resolve()
    if not zip_path.is_file():
        raise PluginInstallError(f"Файл не найден: {zip_path}")

    with tempfile.TemporaryDirectory(prefix="scenaria-plugin-") as tmp:
        extract_root = Path(tmp)
        with zipfile.ZipFile(zip_path, "r") as archive:
            archive.extractall(extract_root)
        manifest = _validate_zip_contents(extract_root)
        resolved_id = str(manifest.get("id", plugin_id or "")).strip()
        if plugin_id and resolved_id != plugin_id:
            raise PluginInstallError(f"Ожидался плагин {plugin_id}, в архиве — {resolved_id}")
        target = _install_extracted(extract_root, manifest)

    reset_registry()
    get_registry().reload()
    return target


def _find_addon_asset(plugin_id: str) -> tuple[str, str]:
    release = _request_json(_api_url("/releases/latest"))
    tag = str(release.get("tag_name", "")).strip()
    assets = release.get("assets") or []
    patterns = (
        f"scenaria-{plugin_id}",
        f"scenaria_{plugin_id}",
        plugin_id,
    )
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name", ""))
        lower = name.lower()
        if not lower.endswith(".zip"):
            continue
        if any(pattern in lower for pattern in patterns):
            return tag, name
    raise PluginInstallError(
        f"На GitHub Releases нет zip для «{plugin_id}» (Scenaria {app_version()})"
    )


def install_from_url(url: str, *, plugin_id: str | None = None) -> Path:
    with tempfile.TemporaryDirectory(prefix="scenaria-plugin-dl-") as tmp:
        zip_path = Path(tmp) / "addon.zip"
        download_url_resilient(url, zip_path)
        return install_from_zip(zip_path, plugin_id=plugin_id)


def install_plugin(
    plugin_id: str,
    *,
    zip_path: Path | None = None,
    url: str | None = None,
) -> Path:
    if zip_path is not None:
        return install_from_zip(zip_path, plugin_id=plugin_id or None)
    if url:
        return install_from_url(url, plugin_id=plugin_id or None)
    try:
        tag, asset_name = _find_addon_asset(plugin_id)
        download_url = _direct_release_url(tag, asset_name)
    except UpdateCheckError as exc:
        raise PluginInstallError(str(exc)) from exc
    return install_from_url(download_url, plugin_id=plugin_id)


def uninstall_plugin(plugin_id: str) -> bool:
    target = paths.plugins_dir() / plugin_id
    if not target.is_dir():
        return False
    shutil.rmtree(target)
    reset_registry()
    get_registry().reload()
    return True
